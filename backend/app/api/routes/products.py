"""Product API routes."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_shop_id
from app.api.deps import require_role
from app.db.models.price_history import PriceHistory
from app.db.models.product import Product
from app.db.models.sale import SaleItem
from app.db.models.stock import StockBatch
from app.db.session import SessionLocal
from app.schemas.product import (
    ProductCreate,
    ProductOut,
    ProductUpdate,
    VariantSummary,
)

router = APIRouter(prefix="/products", tags=["Products"])


# ── Restock request schema ────────────────────────────────────────
class RestockRequest(BaseModel):
    quantity: float = Field(..., gt=0, description="Quantity to add to stock")
    cost_per_unit: Optional[float] = Field(None, ge=0, description="Optional cost per unit")
    notes: Optional[str] = Field(None, max_length=500, description="Optional notes")


def get_db():
    """Yield a database session for route handlers."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _product_to_out(product: Product, variant_count: int = 0) -> dict:
    """Convert a Product ORM object to a dict matching ProductOut."""
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
    """Count variants of this product."""
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


@router.post("/", response_model=ProductOut)
def create_product(
    product: ProductCreate,
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    """Create a new product or variant."""
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
        batch = StockBatch(
            shop_id=shop_id,
            product_id=new_product.id,
            quantity_added=new_product.stock_qty,
            date_added=datetime.utcnow(),
            cost_per_unit=new_product.purchase_price or None,
            notes="Initial stock",
        )
        db.add(batch)
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
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    """List products for the current shop."""
    query = db.query(Product).filter(Product.shop_id == shop_id)

    if not include_deleted:
        query = query.filter(Product.is_deleted == False)
    if not include_archived:
        query = query.filter(Product.archived == False)
    if parents_only:
        query = query.filter(Product.parent_id.is_(None))

    products = query.order_by(Product.name).all()

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
    """Get a single product by ID."""
    product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.shop_id == shop_id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    vc = _variant_count_for(db, product_id, shop_id)
    return _product_to_out(product, variant_count=vc)


# ── Price history ─────────────────────────────────────────────────
@router.get("/{product_id}/price-history")
def get_price_history(
    product_id: str,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    """Return price change history for a product, newest first."""
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


# ── Restock history ───────────────────────────────────────────────
@router.get("/{product_id}/restocks")
def get_restocks(
    product_id: str,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    """Return restock history (stock batches) for a product, newest first."""
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

    # Compute sell-speed summary
    finished_batches = [r for r in result if r["days_to_sell"] is not None]
    avg_days_to_sell = None
    if finished_batches:
        avg_days_to_sell = round(
            sum(r["days_to_sell"] for r in finished_batches) / len(finished_batches),
            1,
        )

    total_restocks = len(result)
    total_quantity = sum(r["quantity_added"] for r in result)

    return {
        "product": {
            "id": product.id,
            "name": product.name,
            "unit": product.unit,
            "current_stock": product.stock_qty or 0,
        },
        "summary": {
            "total_restocks": total_restocks,
            "total_quantity_restocked": total_quantity,
            "avg_days_to_sell": avg_days_to_sell,
            "last_restock_date": result[0]["date_added"] if result else None,
        },
        "batches": result,
    }


# ── Restock (add stock) ───────────────────────────────────────────
@router.post("/{product_id}/restock")
def restock_product(
    product_id: str,
    restock: RestockRequest,
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    """
    Add stock to a product. Creates a new StockBatch and updates product stock_qty.

    Optionally records cost_per_unit and notes for the batch.
    """
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
        # Check if this product has variants — parent products shouldn't have stock
        variant_count = _variant_count_for(db, product_id, shop_id)
        if variant_count > 0:
            raise HTTPException(
                status_code=400,
                detail="Cannot restock a parent product — restock its variants instead",
            )

    if restock.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be positive")

    # Create batch
    batch = StockBatch(
        shop_id=shop_id,
        product_id=product_id,
        quantity_added=restock.quantity,
        date_added=datetime.utcnow(),
        cost_per_unit=restock.cost_per_unit,
        notes=restock.notes,
    )
    db.add(batch)

    # Update product stock
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


# ── Sell speed (moved from analytics) ─────────────────────────────
@router.get("/{product_id}/sell-speed")
def get_sell_speed(
    product_id: str,
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    """
    Return sell-speed analytics for a product based on finished batches.
    """
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
    """List all variants of a parent product."""
    parent = (
        db.query(Product)
        .filter(Product.id == parent_id, Product.shop_id == shop_id)
        .first()
    )
    if not parent:
        raise HTTPException(status_code=404, detail="Parent product not found")

    variants = (
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
    return variants


@router.delete(
    "/{product_id}",
    dependencies=[Depends(require_role("owner"))],
)
def delete_product(
    product_id: str,
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    """Delete a product. Blocks if it has active variants."""
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
        return {"message": "Product soft-deleted (used in sales)"}

    db.delete(product)
    db.commit()
    return {"message": "Product permanently deleted"}


@router.put("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: str,
    product_update: ProductUpdate,
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    """Update product fields. Logs price changes."""
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
            batch = StockBatch(
                shop_id=shop_id,
                product_id=product.id,
                quantity_added=added_qty,
                date_added=datetime.utcnow(),
                notes="Stock adjusted via product edit",
            )
            db.add(batch)
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


@router.put("/restore/{product_id}")
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
    product.is_deleted = False
    db.commit()
    return {"message": "Product restored"}


@router.put("/archive/{product_id}")
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


@router.put("/unarchive/{product_id}")
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