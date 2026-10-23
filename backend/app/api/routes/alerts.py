"""Alerts routes — low stock, debtors, slow movers, summary."""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

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
    """
    Return products at or below their low-stock threshold.

    Each product is classified by urgency:
    - "out_of_stock" — stock_qty <= 0
    - "critical" — stock_qty <= threshold * 0.4
    - "low" — stock_qty <= threshold (but above critical)
    """
    products = (
        db.query(Product)
        .filter(
            Product.stock_qty <= Product.low_stock_threshold,
            Product.shop_id == shop_id,
            Product.is_deleted == False,
            Product.archived == False,
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
    """
    Return customers who owe money and haven't paid in `days` days.

    Includes:
    - Customers with total_credit > 0
    - Whose last payment is older than `days` days (or who never paid)
    """
    cutoff = datetime.utcnow() - timedelta(days=days)

    # Get all customers with outstanding credit
    customers_with_credit = (
        db.query(Customer)
        .filter(
            Customer.total_credit > 0,
            Customer.shop_id == shop_id,
        )
        .all()
    )

    # For each, find last payment date
    result = []
    for c in customers_with_credit:
        last_payment = (
            db.query(func.max(Payment.created_at))
            .filter(Payment.customer_id == c.id, Payment.shop_id == shop_id)
            .scalar()
        )

        # Skip if paid recently
        if last_payment and last_payment >= cutoff:
            continue

        days_since = (datetime.utcnow() - last_payment).days if last_payment else None

        result.append({
            "id": c.id,
            "name": c.name,
            "phone": c.phone,
            "total_credit": c.total_credit or 0,
            "last_payment_date": last_payment.isoformat() if last_payment else None,
            "days_since_last_payment": days_since,
            "never_paid": last_payment is None,
        })

    # Sort by credit amount descending (biggest debtors first)
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
    Return products with stock but no sales in `days` days.

    Only includes top-level products (excludes parent groups with variants).
    """
    cutoff = datetime.utcnow() - timedelta(days=days)

    # Get all in-stock, non-deleted, non-parent products
    products = (
        db.query(Product)
        .filter(
            Product.stock_qty > 0,
            Product.shop_id == shop_id,
            Product.is_deleted == False,
            Product.archived == False,
            Product.parent_id.is_(None),
        )
        .all()
    )

    result = []
    for p in products:
        # Get last sale date (non-voided sales)
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

        # Skip if sold recently
        if last_sale and last_sale >= cutoff:
            continue

        days_since = (datetime.utcnow() - last_sale).days if last_sale else None

        result.append({
            "id": p.id,
            "name": p.name,
            "category": p.category,
            "stock_qty": p.stock_qty or 0,
            "selling_price": p.selling_price or 0,
            "unit": p.unit,
            "last_sale_date": last_sale.isoformat() if last_sale else None,
            "days_since_last_sale": days_since,
            "never_sold": last_sale is None,
        })

    # Sort by days without sale (never sold first, then oldest)
    result.sort(
        key=lambda x: (x["days_since_last_sale"] is not None, x["days_since_last_sale"] or 99999),
        reverse=True,
    )
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
    Counts of each alert type — used for badge on navigation.
    """
    # Low stock count
    low_stock_count = (
        db.query(func.count(Product.id))
        .filter(
            Product.stock_qty <= Product.low_stock_threshold,
            Product.shop_id == shop_id,
            Product.is_deleted == False,
            Product.archived == False,
        )
        .scalar()
        or 0
    )

    # Debtors count (simplified — customers with credit and no recent payment)
    cutoff_debtors = datetime.utcnow() - timedelta(days=debtors_days)
    customers_with_credit = (
        db.query(Customer)
        .filter(Customer.total_credit > 0, Customer.shop_id == shop_id)
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

    # Slow movers count (approximate — products with stock, check last sale)
    cutoff_slow = datetime.utcnow() - timedelta(days=slow_movers_days)
    in_stock_products = (
        db.query(Product)
        .filter(
            Product.stock_qty > 0,
            Product.shop_id == shop_id,
            Product.is_deleted == False,
            Product.archived == False,
            Product.parent_id.is_(None),
        )
        .all()
    )
    slow_count = 0
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

    return {
        "low_stock": low_stock_count,
        "debtors": debtors_count,
        "slow_movers": slow_count,
        "total": low_stock_count + debtors_count + slow_count,
    }