"""Alerts routes — low stock, debtors, slow movers, reorder, summary."""

from datetime import datetime, timedelta
from math import ceil

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, exists, func
from sqlalchemy.orm import Session, aliased

from app.api.dependencies import get_current_shop_id
from app.db.models.customer import Customer
from app.db.models.payment import Payment
from app.db.models.product import Product
from app.db.models.sale import Sale, SaleItem
from app.db.session import SessionLocal

router = APIRouter(prefix="/alerts", tags=["Alerts"])


def get_db():
    """Yield a database session for request dependency injection."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─── Leaf-products helper (variants + standalones, NO parents) ───


def _leaf_product_ids(db: Session, shop_id: str) -> set[str]:
    """
    IDs of products that can actually be sold or restocked.

    A "leaf" is:
      - a variant (parent_id IS NOT NULL), OR
      - a standalone product (parent_id IS NULL AND no children)

    Parents-with-children are excluded — they're containers and should
    never appear in low-stock / slow-mover / reorder alerts.
    """
    parent_ids = {
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

    all_ids = {
        row.id
        for row in db.query(Product.id)
        .filter(
            Product.shop_id == shop_id,
            Product.is_deleted == False,
            Product.archived == False,
        )
        .all()
    }

    return all_ids - parent_ids


# ── Low Stock ────────────────────────────────────────────────────
def _classify_low_stock(stock: float, threshold: float) -> str:
    """Classify urgency of a low-stock product."""
    if stock <= 0:
        return "out_of_stock"
    if threshold > 0 and stock <= threshold * 0.4:
        return "critical"
    return "low"


@router.get("/low-stock")
def low_stock_alert(
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    """Return sellable products at or below their low-stock threshold."""
    leaf_ids = _leaf_product_ids(db, shop_id)
    if not leaf_ids:
        return []

    products = (
        db.query(Product)
        .filter(
            Product.id.in_(leaf_ids),
            Product.stock_qty <= Product.low_stock_threshold,
        )
        .order_by(Product.stock_qty.asc())
        .all()
    )

    result = []
    for p in products:
        result.append({
            "id": p.id,
            "name": p.name,
            "category": p.category,
            "stock_qty": p.stock_qty or 0,
            "low_stock_threshold": p.low_stock_threshold or 5,
            "selling_price": p.selling_price or 0,
            "purchase_price": p.purchase_price or 0,
            "unit": p.unit,
            "severity": _classify_low_stock(p.stock_qty or 0, p.low_stock_threshold or 5),
        })
    return result


# ── Debtors ──────────────────────────────────────────────────────
@router.get("/debtors")
def debtors_alert(
    days: int = Query(14, ge=1, le=365, description="Days since last payment threshold"),
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    """Return customers who owe money and haven't paid in `days` days."""
    cutoff = datetime.utcnow() - timedelta(days=days)

    customers_with_credit = (
        db.query(Customer)
        .filter(
            func.coalesce(Customer.total_credit, 0) > 0,
            Customer.shop_id == shop_id,
        )
        .all()
    )

    result = []
    for c in customers_with_credit:
        last_payment = (
            db.query(func.max(Payment.created_at))
            .filter(Payment.customer_id == c.id, Payment.shop_id == shop_id)
            .scalar()
        )

        if last_payment and last_payment >= cutoff:
            continue

        days_since = (datetime.utcnow() - last_payment).days if last_payment else None

        result.append({
            "id": c.id,
            "name": c.name,
            "phone": c.phone,
            "total_credit": float(c.total_credit or 0),
            "last_payment_date": last_payment.isoformat() if last_payment else None,
            "days_since_last_payment": days_since,
            "never_paid": last_payment is None,
        })

    result.sort(key=lambda x: x["total_credit"], reverse=True)
    return result


# ── Slow Movers ──────────────────────────────────────────────────
@router.get("/slow-movers")
def slow_movers_alert(
    days: int = Query(30, ge=1, le=365, description="Days since last sale threshold"),
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    """
    Return sellable products with stock but no sales in `days` days.

    Each item includes `stuck_value` = stock × purchase_price — the amount
    of cash currently tied up in this slow mover.
    """
    leaf_ids = _leaf_product_ids(db, shop_id)
    if not leaf_ids:
        return []

    cutoff = datetime.utcnow() - timedelta(days=days)

    products = (
        db.query(Product)
        .filter(
            Product.id.in_(leaf_ids),
            Product.stock_qty > 0,
        )
        .all()
    )

    result = []
    for p in products:
        last_sale = (
            db.query(func.max(Sale.created_at))
            .join(SaleItem, SaleItem.sale_id == Sale.id)
            .filter(
                SaleItem.product_id == p.id,
                Sale.shop_id == shop_id,
                Sale.is_voided == False,
            )
            .scalar()
        )

        if last_sale and last_sale >= cutoff:
            continue

        days_since = (datetime.utcnow() - last_sale).days if last_sale else None
        stock = p.stock_qty or 0
        purchase = float(p.purchase_price or 0)
        stuck_value = round(stock * purchase, 2)

        result.append({
            "id": p.id,
            "name": p.name,
            "category": p.category,
            "stock_qty": stock,
            "selling_price": p.selling_price or 0,
            "purchase_price": purchase,
            "stuck_value": stuck_value,
            "unit": p.unit,
            "last_sale_date": last_sale.isoformat() if last_sale else None,
            "days_since_last_sale": days_since,
            "never_sold": last_sale is None,
        })

    result.sort(
        key=lambda x: (
            -x["stuck_value"],  # most capital locked first
            (x["days_since_last_sale"] is not None),
            -(x["days_since_last_sale"] or 99999),
        )
    )
    return result


# ── Reorder Suggestions ──────────────────────────────────────────
def _compute_reorder_suggestions(
    db: Session, shop_id: str, lookback_days: int = 30, target_days: int = 7
) -> dict:
    """
    Classifies into: critical (<3d), soon (<7d), ok (≥7d), no_data.
    Includes: variants + standalones. Excludes: parents-with-children.
    """
    cutoff = datetime.utcnow() - timedelta(days=lookback_days)

    parent_ids_with_variants = {
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

    all_candidates = (
        db.query(Product)
        .filter(
            Product.shop_id == shop_id,
            Product.is_deleted == False,
            Product.archived == False,
        )
        .all()
    )

    products = [
        p
        for p in all_candidates
        if (p.parent_id is not None) or (p.id not in parent_ids_with_variants)
    ]

    if not products:
        return {"critical": [], "soon": [], "ok": [], "no_data": []}

    product_ids = [p.id for p in products]

    sold_rows = (
        db.query(SaleItem.product_id, func.sum(SaleItem.quantity).label("total_qty"))
        .join(Sale, Sale.id == SaleItem.sale_id)
        .filter(
            SaleItem.product_id.in_(product_ids),
            Sale.shop_id == shop_id,
            Sale.is_voided == False,
            Sale.created_at >= cutoff,
        )
        .group_by(SaleItem.product_id)
        .all()
    )
    sold_by_product = {row.product_id: float(row.total_qty or 0) for row in sold_rows}

    critical = []
    soon = []
    ok = []
    no_data = []

    for p in products:
        units_sold = sold_by_product.get(p.id, 0.0)
        stock = p.stock_qty or 0

        if units_sold < 10:
            confidence = "low"
        elif units_sold < 30:
            confidence = "medium"
        else:
            confidence = "high"

        base = {
            "product_id": p.id,
            "name": p.name,
            "category": p.category,
            "unit": p.unit or "unit",
            "stock_qty": stock,
            "selling_price": p.selling_price or 0,
            "purchase_price": p.purchase_price or 0,
            "units_sold_last_period": units_sold,
            "lookback_days": lookback_days,
            "confidence": confidence,
        }

        if units_sold <= 0:
            base["avg_daily_sales"] = 0.0
            base["days_remaining"] = None
            base["suggested_order_qty"] = 0
            base["urgency"] = "no_data"
            no_data.append(base)
            continue

        avg_daily = units_sold / lookback_days
        days_remaining = (stock / avg_daily) if avg_daily > 0 else float("inf")
        suggested_order = max(1, ceil(avg_daily * target_days))

        base["avg_daily_sales"] = round(avg_daily, 2)
        base["days_remaining"] = (
            round(days_remaining, 1) if days_remaining != float("inf") else None
        )
        base["suggested_order_qty"] = suggested_order

        if stock <= 0 or days_remaining < 3:
            base["urgency"] = "critical"
            critical.append(base)
        elif days_remaining < 7:
            base["urgency"] = "soon"
            soon.append(base)
        else:
            base["urgency"] = "ok"
            ok.append(base)

    critical.sort(
        key=lambda x: x["days_remaining"] if x["days_remaining"] is not None else -1
    )
    soon.sort(
        key=lambda x: x["days_remaining"] if x["days_remaining"] is not None else 9999
    )
    ok.sort(key=lambda x: x["days_remaining"] if x["days_remaining"] is not None else 9999)
    no_data.sort(key=lambda x: x["name"])

    return {
        "critical": critical,
        "soon": soon,
        "ok": ok,
        "no_data": no_data,
    }


@router.get("/reorder-suggestions")
def reorder_suggestions(
    lookback_days: int = Query(30, ge=7, le=90),
    target_days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    result = _compute_reorder_suggestions(db, shop_id, lookback_days, target_days)
    result["generated_at"] = datetime.utcnow().isoformat()
    result["lookback_days"] = lookback_days
    result["target_days"] = target_days
    return result


# ── Summary ──────────────────────────────────────────────────────
@router.get("/summary")
def alerts_summary(
    debtors_days: int = Query(14, ge=1, le=365),
    slow_movers_days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    """
    Counts used for the tab badges.

    Returns both the "aging" counts (what shows on tabs) and *_all
    counts (all-time). The UI uses *_all to differentiate "no debtors
    at all" from "no debtors older than 14 days".
    """
    leaf_ids = _leaf_product_ids(db, shop_id)

    # Low stock (aging = same as all; there is no "aging" for stock)
    if leaf_ids:
        low_stock_count = (
            db.query(func.count(Product.id))
            .filter(
                Product.id.in_(leaf_ids),
                Product.stock_qty <= Product.low_stock_threshold,
            )
            .scalar()
            or 0
        )
    else:
        low_stock_count = 0

    # Debtors
    cutoff_debtors = datetime.utcnow() - timedelta(days=debtors_days)
    customers_with_credit = (
        db.query(Customer)
        .filter(
            func.coalesce(Customer.total_credit, 0) > 0,
            Customer.shop_id == shop_id,
        )
        .all()
    )
    debtors_count = 0
    for c in customers_with_credit:
        last_payment = (
            db.query(func.max(Payment.created_at))
            .filter(Payment.customer_id == c.id, Payment.shop_id == shop_id)
            .scalar()
        )
        if not last_payment or last_payment < cutoff_debtors:
            debtors_count += 1

    debtors_all = len(customers_with_credit)

    # Slow movers
    cutoff_slow = datetime.utcnow() - timedelta(days=slow_movers_days)
    slow_count = 0
    slow_movers_all = 0
    if leaf_ids:
        in_stock_products = (
            db.query(Product)
            .filter(
                Product.id.in_(leaf_ids),
                Product.stock_qty > 0,
            )
            .all()
        )
        slow_movers_all = len(in_stock_products)
        for p in in_stock_products:
            last_sale = (
                db.query(func.max(Sale.created_at))
                .join(SaleItem, SaleItem.sale_id == Sale.id)
                .filter(
                    SaleItem.product_id == p.id,
                    Sale.shop_id == shop_id,
                    Sale.is_voided == False,
                )
                .scalar()
            )
            if not last_sale or last_sale < cutoff_slow:
                slow_count += 1

    # Reorder count (critical + soon)
    reorder_data = _compute_reorder_suggestions(db, shop_id)
    reorder_count = len(reorder_data["critical"]) + len(reorder_data["soon"])

    return {
        "low_stock": low_stock_count,
        "low_stock_all": low_stock_count,  # same — no aging concept
        "debtors": debtors_count,
        "debtors_all": debtors_all,
        "slow_movers": slow_count,
        "slow_movers_all": slow_movers_all,
        "reorder": reorder_count,
        "total": low_stock_count + debtors_count + slow_count + reorder_count,
    }