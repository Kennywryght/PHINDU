"""Product API routes."""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_shop_id
from app.api.deps import require_role
from app.db.models.price_history import PriceHistory
from app.db.models.product import Product
from app.db.models.sale import Sale, SaleItem
from app.db.models.stock import StockBatch
from app.db.session import SessionLocal
from app.schemas.product import (
    BulkProductCreate,
    ProductCreate,
    ProductOut,
    ProductUpdate,
    VariantSummary,
)

router = APIRouter(prefix="/products", tags=["Products"])


# ── Schemas ───────────────────────────────────────────────────────
class RestockRequest(BaseModel):
    quantity: float = Field(..., gt=0, description="Quantity to add to stock")
    cost_per_unit: Optional[float] = Field(None, ge=0, description="Optional cost per unit")
    notes: Optional[str] = Field(None, max_length=500, description="Optional notes")


class BatchRestockItem(BaseModel):
    product_id: str
    quantity: float = Field(..., gt=0)
    cost_per_unit: Optional[float] = Field(None, ge=0)
    notes: Optional[str] = Field(None, max_length=500)


class BatchRestockRequest(BaseModel):
    items: list[BatchRestockItem] = Field(..., min_length=1)


class BulkIdsRequest(BaseModel):
    product_ids: list[str] = Field(..., min_length=1)


class BulkRestockItem(BaseModel):
    product_id: str
    quantity: float = Field(..., gt=0)


class BulkRestockRequest(BaseModel):
    items: list[BulkRestockItem] = Field(..., min_length=1)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _product_to_out(product: Product, variant_count: int = 0) -> dict:
    return {
        "id": product.id,
        "shop_id": product.shop_id,
        "name": product.name,
        "category": product.category,
        "type": product.type,
        "unit": product.unit,
        "selling_price": product.selling_price or 0,
        "purchase_price": product.purchase_price or 0,
        "stock_qty": product.stock_qty or 0,
        "archived": product.archived or False,
        "is_deleted": product.is_deleted or False,
        "parent_id": product.parent_id,
        "low_stock_threshold": product.low_stock_threshold or 5,
        "is_parent": variant_count > 0,
        "variant_count": variant_count,
    }


def _variant_count_for(db: Session, product_id: str, shop_id: str) -> int:
    return (
        db.query(func.count(Product.id))
        .filter(
            Product.parent_id == product_id,
            Product.shop_id == shop_id,
            Product.is_deleted == False,
        )
        .scalar()
        or 0
    )


# ─────────────────────────────────────────────────────────────────
# LITERAL PATHS FIRST (FastAPI matches in declaration order)
# ─────────────────────────────────────────────────────────────────


@router.get("/categories")
def list_categories(
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    """Return distinct categories used in this shop with usage counts."""
    rows = (
        db.query(
            Product.category,
            func.count(Product.id).label("count"),
        )
        .filter(
            Product.shop_id == shop_id,
            Product.is_deleted == False,
            Product.category.isnot(None),
            Product.category != "",
        )
        .group_by(Product.category)
        .order_by(Product.category)
        .all()
    )

    return [
        {"name": r.category, "count": int(r.count or 0)}
        for r in rows
        if r.category
    ]


@router.post("/batch-restock")
def batch_restock(
    payload: BatchRestockRequest,
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    """Restock multiple products in one atomic transaction (CSV flow)."""
    product_ids = [item.product_id for item in payload.items]
    products = (
        db.query(Product)
        .filter(Product.id.in_(product_ids), Product.shop_id == shop_id)
        .all()
    )
    by_id = {p.id: p for p in products}

    missing = [pid for pid in product_ids if pid not in by_id]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Products not found in this shop: {', '.join(missing)}",
        )

    deleted = [p.name for p in products if p.is_deleted]
    if deleted:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot restock deleted products: {', '.join(deleted)}",
        )

    for item in payload.items:
        product = by_id[item.product_id]
        if product.parent_id is None:
            vc = _variant_count_for(db, product.id, shop_id)
            if vc > 0:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Cannot restock parent product '{product.name}' — "
                        f"restock its {vc} variant(s) instead"
                    ),
                )

    now = datetime.utcnow()
    created_batches = []
    for item in payload.items:
        product = by_id[item.product_id]
        batch = StockBatch(
            shop_id=shop_id,
            product_id=product.id,
            quantity_added=item.quantity,
            date_added=now,
            cost_per_unit=item.cost_per_unit,
            notes=item.notes or "Batch restock",
        )
        db.add(batch)
        product.stock_qty = (product.stock_qty or 0) + item.quantity
        created_batches.append((batch, product, item.quantity))

    db.commit()

    for batch, product, _qty in created_batches:
        db.refresh(batch)
        db.refresh(product)

    return {
        "message": f"Restocked {len(payload.items)} product(s) successfully",
        "items": [
            {
                "product_id": product.id,
                "product_name": product.name,
                "quantity_added": qty,
                "new_stock": product.stock_qty or 0,
                "batch_id": batch.id,
            }
            for batch, product, qty in created_batches
        ],
    }


# ─────────────────────────────────────────────────────────────────
# TIER 3.3: Bulk product creation (Variant Wizard)
# ─────────────────────────────────────────────────────────────────


@router.post("/bulk")
def bulk_create_product(
    payload: BulkProductCreate,
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    """Create one parent (or standalone) product + N variants atomically."""
    if payload.has_variants and len(payload.variants) == 0:
        raise HTTPException(
            status_code=400,
            detail="has_variants=True requires at least one variant",
        )

    if not payload.has_variants and payload.selling_price <= 0:
        raise HTTPException(
            status_code=400,
            detail="Standalone product requires selling_price > 0",
        )

    if payload.has_variants:
        seen = set()
        for v in payload.variants:
            key = v.name.strip().lower()
            if key in seen:
                raise HTTPException(
                    status_code=400,
                    detail=f"Duplicate variant name: {v.name}",
                )
            seen.add(key)

    try:
        parent = Product(
            shop_id=shop_id,
            name=payload.name.strip(),
            category=payload.category,
            type=payload.type,
            unit=payload.unit,
            selling_price=0 if payload.has_variants else (payload.selling_price or 0),
            purchase_price=0 if payload.has_variants else (payload.purchase_price or 0),
            stock_qty=0 if payload.has_variants else (payload.stock_qty or 0),
            parent_id=None,
            low_stock_threshold=payload.low_stock_threshold or 5,
        )
        db.add(parent)
        db.flush()

        if not payload.has_variants:
            if parent.selling_price and parent.selling_price > 0:
                db.add(
                    PriceHistory(
                        product_id=parent.id,
                        old_price=None,
                        new_price=parent.selling_price,
                        price_type="selling",
                    )
                )
            if parent.purchase_price and parent.purchase_price > 0:
                db.add(
                    PriceHistory(
                        product_id=parent.id,
                        old_price=None,
                        new_price=parent.purchase_price,
                        price_type="purchase",
                    )
                )
            if parent.stock_qty and parent.stock_qty > 0:
                db.add(
                    StockBatch(
                        shop_id=shop_id,
                        product_id=parent.id,
                        quantity_added=parent.stock_qty,
                        date_added=datetime.utcnow(),
                        cost_per_unit=parent.purchase_price or None,
                        notes="Initial stock",
                    )
                )

        created_variants: list[Product] = []
        if payload.has_variants:
            now = datetime.utcnow()
            for v in payload.variants:
                child = Product(
                    shop_id=shop_id,
                    name=v.name.strip(),
                    category=payload.category,
                    type=payload.type,
                    unit=payload.unit,
                    selling_price=v.selling_price,
                    purchase_price=v.purchase_price,
                    stock_qty=v.stock_qty,
                    parent_id=parent.id,
                    low_stock_threshold=v.low_stock_threshold or 5,
                )
                db.add(child)
                db.flush()

                if child.selling_price > 0:
                    db.add(
                        PriceHistory(
                            product_id=child.id,
                            old_price=None,
                            new_price=child.selling_price,
                            price_type="selling",
                        )
                    )
                if child.purchase_price > 0:
                    db.add(
                        PriceHistory(
                            product_id=child.id,
                            old_price=None,
                            new_price=child.purchase_price,
                            price_type="purchase",
                        )
                    )
                if child.stock_qty > 0:
                    db.add(
                        StockBatch(
                            shop_id=shop_id,
                            product_id=child.id,
                            quantity_added=child.stock_qty,
                            date_added=now,
                            cost_per_unit=child.purchase_price or None,
                            notes="Initial stock",
                        )
                    )
                created_variants.append(child)

        db.commit()

    except Exception:
        db.rollback()
        raise

    db.refresh(parent)
    for v in created_variants:
        db.refresh(v)

    vc = _variant_count_for(db, parent.id, shop_id)
    return {
        "parent": _product_to_out(parent, variant_count=vc),
        "variants": [_product_to_out(v) for v in created_variants],
        "variant_count": len(created_variants),
    }


# ─────────────────────────────────────────────────────────────────
# TIER 4.2: Bulk actions
# ─────────────────────────────────────────────────────────────────


def _load_products_for_bulk(
    db: Session, shop_id: str, product_ids: list[str]
) -> list[Product]:
    """Fetch, validate ownership, and refuse missing ids. All-or-nothing."""
    products = (
        db.query(Product)
        .filter(Product.id.in_(product_ids), Product.shop_id == shop_id)
        .all()
    )
    by_id = {p.id: p for p in products}
    missing = [pid for pid in product_ids if pid not in by_id]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Products not found in this shop: {', '.join(missing)}",
        )
    return products


@router.post(
    "/bulk-archive",
    dependencies=[Depends(require_role("owner", "manager"))],
)
def bulk_archive(
    payload: BulkIdsRequest,
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    products = _load_products_for_bulk(db, shop_id, payload.product_ids)
    changed = 0
    for p in products:
        if not p.archived:
            p.archived = True
            changed += 1
    db.commit()
    return {
        "message": f"Archived {changed} product(s)",
        "affected": changed,
        "total": len(products),
    }


@router.post(
    "/bulk-unarchive",
    dependencies=[Depends(require_role("owner", "manager"))],
)
def bulk_unarchive(
    payload: BulkIdsRequest,
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    products = _load_products_for_bulk(db, shop_id, payload.product_ids)
    changed = 0
    for p in products:
        if p.archived:
            p.archived = False
            changed += 1
    db.commit()
    return {"message": f"Unarchived {changed} product(s)", "affected": changed}


@router.post(
    "/bulk-soft-delete",
    dependencies=[Depends(require_role("owner"))],
)
def bulk_soft_delete(
    payload: BulkIdsRequest,
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    products = _load_products_for_bulk(db, shop_id, payload.product_ids)
    changed = 0
    for p in products:
        if not p.is_deleted:
            p.is_deleted = True
            changed += 1
    db.commit()
    return {
        "message": f"Moved {changed} product(s) to Deleted",
        "affected": changed,
        "total": len(products),
    }


@router.post(
    "/bulk-restore",
    dependencies=[Depends(require_role("owner"))],
)
def bulk_restore(
    payload: BulkIdsRequest,
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    products = _load_products_for_bulk(db, shop_id, payload.product_ids)
    changed = 0
    for p in products:
        if p.is_deleted:
            p.is_deleted = False
            changed += 1
    db.commit()
    return {"message": f"Restored {changed} product(s)", "affected": changed}


@router.post(
    "/bulk-restock",
    dependencies=[Depends(require_role("owner", "manager"))],
)
def bulk_restock(
    payload: BulkRestockRequest,
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    """Thin wrapper over /batch-restock for the "bulk select → restock" flow."""
    product_ids = [item.product_id for item in payload.items]
    products = _load_products_for_bulk(db, shop_id, product_ids)
    by_id = {p.id: p for p in products}

    deleted = [p.name for p in products if p.is_deleted]
    if deleted:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot restock deleted products: {', '.join(deleted)}",
        )

    for item in payload.items:
        product = by_id[item.product_id]
        if product.parent_id is None:
            vc = _variant_count_for(db, product.id, shop_id)
            if vc > 0:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Cannot restock parent product '{product.name}' — "
                        f"restock its variants instead"
                    ),
                )

    now = datetime.utcnow()
    for item in payload.items:
        product = by_id[item.product_id]
        db.add(
            StockBatch(
                shop_id=shop_id,
                product_id=product.id,
                quantity_added=item.quantity,
                date_added=now,
                notes="Bulk restock",
            )
        )
        product.stock_qty = (product.stock_qty or 0) + item.quantity

    db.commit()
    return {"message": f"Restocked {len(payload.items)} product(s)"}


# ─────────────────────────────────────────────────────────────────
# CRUD + everything else
# ─────────────────────────────────────────────────────────────────


@router.post("/", response_model=ProductOut)
def create_product(
    product: ProductCreate,
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    if product.parent_id:
        parent = (
            db.query(Product)
            .filter(Product.id == product.parent_id, Product.shop_id == shop_id)
            .first()
        )
        if not parent:
            raise HTTPException(status_code=404, detail="Parent product not found")
        if parent.parent_id is not None:
            raise HTTPException(
                status_code=400,
                detail="Cannot nest variants — parent must be a top-level product",
            )
        if parent.is_deleted:
            raise HTTPException(status_code=400, detail="Cannot add variant to deleted product")

    new_product = Product(
        shop_id=shop_id,
        name=product.name,
        category=product.category,
        type=product.type,
        unit=product.unit,
        selling_price=product.selling_price or 0,
        purchase_price=product.purchase_price or 0,
        stock_qty=product.stock_qty or 0,
        parent_id=product.parent_id,
        low_stock_threshold=product.low_stock_threshold or 5,
    )

    db.add(new_product)
    db.commit()
    db.refresh(new_product)

    if new_product.stock_qty and new_product.stock_qty > 0:
        db.add(
            StockBatch(
                shop_id=shop_id,
                product_id=new_product.id,
                quantity_added=new_product.stock_qty,
                date_added=datetime.utcnow(),
                cost_per_unit=new_product.purchase_price or None,
                notes="Initial stock",
            )
        )
        db.commit()

    if new_product.selling_price and new_product.selling_price > 0:
        db.add(
            PriceHistory(
                product_id=new_product.id,
                old_price=None,
                new_price=new_product.selling_price,
                price_type="selling",
            )
        )
    if new_product.purchase_price and new_product.purchase_price > 0:
        db.add(
            PriceHistory(
                product_id=new_product.id,
                old_price=None,
                new_price=new_product.purchase_price,
                price_type="purchase",
            )
        )
    db.commit()

    return _product_to_out(new_product)


@router.get("/", response_model=list[ProductOut])
def get_products(
    include_deleted: bool = False,
    parents_only: bool = Query(False),
    include_archived: bool = Query(True),
    leaf_only: bool = Query(
        False,
        description=(
            "Return only sellable leaves: variants (parent_id set) and "
            "standalone products (parent_id null AND no variant children). "
            "Parents WITH children are excluded. Used by POS."
        ),
    ),
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    query = db.query(Product).filter(Product.shop_id == shop_id)

    if not include_deleted:
        query = query.filter(Product.is_deleted == False)
    if not include_archived:
        query = query.filter(Product.archived == False)
    if parents_only:
        query = query.filter(Product.parent_id.is_(None))

    products = query.order_by(Product.name).all()

    # If leaf_only, exclude parents that have children
    if leaf_only:
        parent_ids_with_children = {
            row.parent_id
            for row in db.query(Product.parent_id)
            .filter(
                Product.shop_id == shop_id,
                Product.parent_id.isnot(None),
                Product.is_deleted == False,
            )
            .distinct()
            .all()
            if row.parent_id
        }
        products = [p for p in products if p.id not in parent_ids_with_children]

    result = []
    for p in products:
        vc = _variant_count_for(db, p.id, shop_id)
        result.append(_product_to_out(p, variant_count=vc))
    return result


@router.get("/{product_id}", response_model=ProductOut)
def get_product(
    product_id: str,
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.shop_id == shop_id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    vc = _variant_count_for(db, product_id, shop_id)
    return _product_to_out(product, variant_count=vc)


@router.get("/{product_id}/price-history")
def get_price_history(
    product_id: str,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.shop_id == shop_id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    history = (
        db.query(PriceHistory)
        .filter(PriceHistory.product_id == product_id)
        .order_by(PriceHistory.changed_at.desc())
        .limit(limit)
        .all()
    )

    result = []
    for h in history:
        old = h.old_price or 0
        new = h.new_price or 0
        change_pct = None
        if old > 0:
            change_pct = round((new - old) / old * 100, 2)
        result.append({
            "id": h.id,
            "price_type": h.price_type or "selling",
            "old_price": old,
            "new_price": new,
            "change_percent": change_pct,
            "changed_at": h.changed_at.isoformat() if h.changed_at else None,
        })

    current_margin = None
    if product.selling_price and product.selling_price > 0:
        current_margin = round(
            (product.selling_price - (product.purchase_price or 0))
            / product.selling_price
            * 100,
            2,
        )

    return {
        "product": {
            "id": product.id,
            "name": product.name,
            "unit": product.unit,
            "current_selling_price": product.selling_price or 0,
            "current_purchase_price": product.purchase_price or 0,
            "current_margin_percent": current_margin,
        },
        "history": result,
    }


@router.get("/{product_id}/restocks")
def get_restocks(
    product_id: str,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.shop_id == shop_id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    batches = (
        db.query(StockBatch)
        .filter(StockBatch.product_id == product_id, StockBatch.shop_id == shop_id)
        .order_by(StockBatch.date_added.desc())
        .limit(limit)
        .all()
    )

    result = []
    for b in batches:
        days_to_sell = None
        if b.date_finished and b.date_added:
            days_to_sell = max(0, (b.date_finished - b.date_added).days)

        result.append({
            "id": b.id,
            "quantity_added": b.quantity_added or 0,
            "cost_per_unit": b.cost_per_unit,
            "total_cost": (
                (b.quantity_added or 0) * (b.cost_per_unit or 0)
                if b.cost_per_unit
                else None
            ),
            "notes": b.notes,
            "date_added": b.date_added.isoformat() if b.date_added else None,
            "date_finished": b.date_finished.isoformat() if b.date_finished else None,
            "days_to_sell": days_to_sell,
            "is_active": b.date_finished is None,
        })

    finished_batches = [r for r in result if r["days_to_sell"] is not None]
    avg_days_to_sell = None
    if finished_batches:
        avg_days_to_sell = round(
            sum(r["days_to_sell"] for r in finished_batches) / len(finished_batches),
            1,
        )

    return {
        "product": {
            "id": product.id,
            "name": product.name,
            "unit": product.unit,
            "current_stock": product.stock_qty or 0,
        },
        "summary": {
            "total_restocks": len(result),
            "total_quantity_restocked": sum(r["quantity_added"] for r in result),
            "avg_days_to_sell": avg_days_to_sell,
            "last_restock_date": result[0]["date_added"] if result else None,
        },
        "batches": result,
    }


@router.post("/{product_id}/restock")
def restock_product(
    product_id: str,
    restock: RestockRequest,
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.shop_id == shop_id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if product.is_deleted:
        raise HTTPException(status_code=400, detail="Cannot restock deleted product")
    if product.parent_id is None:
        vc = _variant_count_for(db, product_id, shop_id)
        if vc > 0:
            raise HTTPException(
                status_code=400,
                detail="Cannot restock a parent product — restock its variants instead",
            )

    if restock.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be positive")

    batch = StockBatch(
        shop_id=shop_id,
        product_id=product_id,
        quantity_added=restock.quantity,
        date_added=datetime.utcnow(),
        cost_per_unit=restock.cost_per_unit,
        notes=restock.notes,
    )
    db.add(batch)
    product.stock_qty = (product.stock_qty or 0) + restock.quantity

    db.commit()
    db.refresh(product)
    db.refresh(batch)

    return {
        "message": f"Added {restock.quantity} {product.unit or 'units'} to {product.name}",
        "product": _product_to_out(product),
        "batch": {
            "id": batch.id,
            "quantity_added": batch.quantity_added,
            "cost_per_unit": batch.cost_per_unit,
            "date_added": batch.date_added.isoformat() if batch.date_added else None,
        },
    }


@router.get("/{product_id}/sell-speed")
def get_sell_speed(
    product_id: str,
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.shop_id == shop_id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    batches = (
        db.query(StockBatch)
        .filter(
            StockBatch.product_id == product_id,
            StockBatch.shop_id == shop_id,
            StockBatch.date_finished.isnot(None),
        )
        .all()
    )

    if not batches:
        return {
            "product_id": product_id,
            "avg_days_to_sell": None,
            "avg_units_per_day": None,
            "batches_analyzed": 0,
        }

    total_days = 0
    total_qty = 0
    for b in batches:
        if b.date_added and b.date_finished:
            days = max(1, (b.date_finished - b.date_added).days)
            total_days += days
            total_qty += b.quantity_added or 0

    avg_days = round(total_days / len(batches), 1) if batches else None
    avg_units_per_day = round(total_qty / total_days, 2) if total_days > 0 else None

    return {
        "product_id": product_id,
        "avg_days_to_sell": avg_days,
        "avg_units_per_day": avg_units_per_day,
        "batches_analyzed": len(batches),
    }


@router.get("/{parent_id}/variants", response_model=list[VariantSummary])
def get_variants(
    parent_id: str,
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    parent = (
        db.query(Product)
        .filter(Product.id == parent_id, Product.shop_id == shop_id)
        .first()
    )
    if not parent:
        raise HTTPException(status_code=404, detail="Parent product not found")

    return (
        db.query(Product)
        .filter(
            Product.parent_id == parent_id,
            Product.shop_id == shop_id,
            Product.is_deleted == False,
            Product.archived == False,
        )
        .order_by(Product.name)
        .all()
    )


# ─────────────────────────────────────────────────────────────────
# DELETION FAMILY
# ─────────────────────────────────────────────────────────────────


@router.put(
    "/soft-delete/{product_id}",
    dependencies=[Depends(require_role("owner"))],
)
def soft_delete_product(
    product_id: str,
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.shop_id == shop_id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if product.is_deleted:
        return {"message": "Product is already in the Deleted tab"}

    product.is_deleted = True
    db.commit()
    return {
        "message": "Product moved to Deleted tab (recoverable)",
        "product_id": product.id,
        "is_deleted": True,
    }


@router.put(
    "/restore/{product_id}",
    dependencies=[Depends(require_role("owner"))],
)
def restore_product(
    product_id: str,
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.shop_id == shop_id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if not product.is_deleted:
        return {"message": "Product is not in the Deleted tab"}

    product.is_deleted = False
    db.commit()
    return {"message": "Product restored"}


@router.delete(
    "/{product_id}",
    dependencies=[Depends(require_role("owner"))],
)
def permanent_delete_product(
    product_id: str,
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.shop_id == shop_id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    variant_count = _variant_count_for(db, product_id, shop_id)
    if variant_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"This product has {variant_count} variant(s). Delete variants first.",
        )

    sale_exists = db.query(SaleItem).filter(SaleItem.product_id == product_id).first()

    if sale_exists:
        product.is_deleted = True
        db.commit()
        return {
            "message": (
                "Product appears in sales history — cannot be fully removed. "
                "Moved to Deleted tab instead."
            ),
            "soft_deleted": True,
        }

    db.delete(product)
    db.commit()
    return {"message": "Product permanently deleted", "soft_deleted": False}


@router.put(
    "/archive/{product_id}",
    dependencies=[Depends(require_role("owner", "manager"))],
)
def archive_product(
    product_id: str,
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.shop_id == shop_id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    product.archived = True
    db.commit()
    return {"message": "Product archived"}


@router.put(
    "/unarchive/{product_id}",
    dependencies=[Depends(require_role("owner", "manager"))],
)
def unarchive_product(
    product_id: str,
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.shop_id == shop_id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    product.archived = False
    db.commit()
    return {"message": "Product unarchived"}


@router.put("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: str,
    product_update: ProductUpdate,
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.shop_id == shop_id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    update_data = product_update.model_dump(exclude_unset=True)

    if "selling_price" in update_data and update_data["selling_price"] is not None:
        new_selling = update_data["selling_price"]
        if new_selling != product.selling_price:
            db.add(
                PriceHistory(
                    product_id=product.id,
                    old_price=product.selling_price,
                    new_price=new_selling,
                    price_type="selling",
                )
            )

    if "purchase_price" in update_data and update_data["purchase_price"] is not None:
        new_purchase = update_data["purchase_price"]
        if new_purchase != product.purchase_price:
            db.add(
                PriceHistory(
                    product_id=product.id,
                    old_price=product.purchase_price,
                    new_price=new_purchase,
                    price_type="purchase",
                )
            )

    if "stock_qty" in update_data and update_data["stock_qty"] is not None:
        new_stock = update_data["stock_qty"]
        current_stock = product.stock_qty or 0
        if new_stock > current_stock:
            added_qty = new_stock - current_stock
            db.add(
                StockBatch(
                    shop_id=shop_id,
                    product_id=product.id,
                    quantity_added=added_qty,
                    date_added=datetime.utcnow(),
                    notes="Stock adjusted via product edit",
                )
            )
        product.stock_qty = new_stock

    for field, value in update_data.items():
        if field not in ("stock_qty", "selling_price", "purchase_price"):
            setattr(product, field, value)
        elif field == "selling_price":
            product.selling_price = value
        elif field == "purchase_price":
            product.purchase_price = value

    db.commit()
    db.refresh(product)
    vc = _variant_count_for(db, product_id, shop_id)
    return _product_to_out(product, variant_count=vc)


@router.get("/{product_id}/restock-prediction")
def get_restock_prediction(
    product_id: str,
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.shop_id == shop_id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    now = datetime.utcnow()
    current_stock = product.stock_qty or 0

    finished_batches = (
        db.query(StockBatch)
        .filter(
            StockBatch.product_id == product_id,
            StockBatch.shop_id == shop_id,
            StockBatch.date_finished.isnot(None),
        )
        .order_by(StockBatch.date_finished.desc())
        .all()
    )

    latest_batch = (
        db.query(StockBatch)
        .filter(
            StockBatch.product_id == product_id,
            StockBatch.shop_id == shop_id,
        )
        .order_by(StockBatch.date_added.desc())
        .first()
    )

    last_restock_date = latest_batch.date_added if latest_batch else None

    if len(finished_batches) >= 2:
        total_days = 0
        valid_count = 0
        for b in finished_batches:
            if b.date_added and b.date_finished:
                days = (b.date_finished - b.date_added).days
                if days >= 0:
                    total_days += days
                    valid_count += 1

        if valid_count >= 2:
            avg_batch_life_days = round(total_days / valid_count, 1)
            predicted_next = (
                last_restock_date + timedelta(days=avg_batch_life_days)
                if last_restock_date
                else None
            )
            days_until = (predicted_next - now).days if predicted_next else None

            return {
                "product_id": product.id,
                "name": product.name,
                "unit": product.unit or "unit",
                "current_stock": current_stock,
                "avg_batch_life_days": avg_batch_life_days,
                "last_restock_date": (
                    last_restock_date.isoformat() if last_restock_date else None
                ),
                "predicted_next_restock": (
                    predicted_next.isoformat() if predicted_next else None
                ),
                "days_until_restock": days_until,
                "confidence": "high" if valid_count >= 3 else "medium",
                "batches_analyzed": valid_count,
                "method": "batch_life",
            }

    cutoff = now - timedelta(days=30)
    sold_total = (
        db.query(func.sum(SaleItem.quantity))
        .join(Sale, Sale.id == SaleItem.sale_id)
        .filter(
            SaleItem.product_id == product_id,
            Sale.shop_id == shop_id,
            Sale.is_voided == False,
            Sale.created_at >= cutoff,
        )
        .scalar()
        or 0
    )

    if sold_total > 0:
        avg_daily = float(sold_total) / 30.0
        days_until = round(current_stock / avg_daily, 1) if avg_daily > 0 else None
        predicted_next = (
            now + timedelta(days=days_until) if days_until is not None else None
        )

        return {
            "product_id": product.id,
            "name": product.name,
            "unit": product.unit or "unit",
            "current_stock": current_stock,
            "avg_batch_life_days": None,
            "last_restock_date": (
                last_restock_date.isoformat() if last_restock_date else None
            ),
            "predicted_next_restock": (
                predicted_next.isoformat() if predicted_next else None
            ),
            "days_until_restock": days_until,
            "confidence": "low",
            "batches_analyzed": len(finished_batches),
            "method": "sales_velocity",
        }

    return {
        "product_id": product.id,
        "name": product.name,
        "unit": product.unit or "unit",
        "current_stock": current_stock,
        "avg_batch_life_days": None,
        "last_restock_date": (
            last_restock_date.isoformat() if last_restock_date else None
        ),
        "predicted_next_restock": None,
        "days_until_restock": None,
        "confidence": "low",
        "batches_analyzed": len(finished_batches),
        "method": "no_data",
    }