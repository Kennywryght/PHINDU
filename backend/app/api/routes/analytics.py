"""Analytics routes."""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Integer, cast, extract, func
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_shop_id
from app.db.models.expense import Expense
from app.db.models.price_history import PriceHistory
from app.db.models.product import Product
from app.db.models.sale import Sale, SaleItem
from app.db.models.stock import StockBatch
from app.db.session import engine, get_db

router = APIRouter(prefix="/analytics", tags=["Analytics"])

# SQLite does not support EXTRACT(hour FROM ...). Use strftime instead.
_IS_SQLITE = engine.url.drivername.startswith("sqlite")


def _compute_peak_hours_array(db: Session, shop_id: str) -> list[int]:
    """Shared helper: 24-slot array of sale counts per hour."""
    if _IS_SQLITE:
        hour_expr = cast(func.strftime("%H", Sale.created_at), Integer).label("hour")
    else:
        hour_expr = extract("hour", Sale.created_at).label("hour")

    results = (
        db.query(hour_expr, func.count(Sale.id).label("count"))
        .filter(Sale.shop_id == shop_id)
        .group_by(hour_expr)
        .order_by(hour_expr)
        .all()
    )

    hours = [0] * 24
    for r in results:
        if r.hour is not None:
            hours[int(r.hour)] = r.count
    return hours


def _compute_top_products(db: Session, shop_id: str, period: str) -> list[dict]:
    """Shared helper: top products by quantity in period."""
    now = datetime.utcnow()
    if period == "day":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start_date = now - timedelta(days=now.weekday())
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "month":
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        start_date = now - timedelta(days=30)

    results = (
        db.query(Product.id, Product.name, func.sum(SaleItem.quantity).label("total_quantity"))
        .join(SaleItem, SaleItem.product_id == Product.id)
        .join(Sale, Sale.id == SaleItem.sale_id)
        .filter(Sale.shop_id == shop_id, Sale.created_at >= start_date, Sale.created_at <= now)
        .group_by(Product.id, Product.name)
        .order_by(func.sum(SaleItem.quantity).desc())
        .limit(10)
        .all()
    )

    return [{"id": r.id, "name": r.name, "quantity": float(r.total_quantity or 0)} for r in results]


def _compute_profit_margins(db: Session, shop_id: str) -> list[dict]:
    """Shared helper: profit margin per product."""
    results = (
        db.query(
            Product.id,
            Product.name,
            func.sum(SaleItem.total_price).label("revenue"),
            func.sum(SaleItem.cost_price).label("cost"),
        )
        .join(SaleItem, SaleItem.product_id == Product.id)
        .join(Sale, Sale.id == SaleItem.sale_id)
        .filter(Sale.shop_id == shop_id)
        .group_by(Product.id, Product.name)
        .all()
    )

    margins = []
    for r in results:
        revenue = float(r.revenue or 0)
        cost = float(r.cost or 0)
        profit = revenue - cost
        margin_percent = (profit / revenue * 100) if revenue > 0 else 0.0
        margins.append({
            "id": r.id,
            "name": r.name,
            "revenue": revenue,
            "cost": cost,
            "profit": profit,
            "margin_percent": round(margin_percent, 2),
        })

    margins.sort(key=lambda x: x["margin_percent"], reverse=True)
    return margins


def _compute_expense_breakdown(db: Session, shop_id: str) -> list[dict]:
    """Shared helper: expenses grouped by category."""
    results = (
        db.query(Expense.category, func.sum(Expense.amount).label("total"))
        .filter(Expense.shop_id == shop_id)
        .group_by(Expense.category)
        .all()
    )
    return [{"category": r.category or "Uncategorized", "total": float(r.total)} for r in results]


def _compute_recent_price_changes(db: Session, shop_id: str, days: int = 30, limit: int = 5) -> list[dict]:
    """
    Shared helper: recent price changes across all non-parent products.

    Single query against PriceHistory — no N+1 loop needed.
    """
    cutoff = datetime.utcnow() - timedelta(days=days)

    # Get all recent price changes for this shop's products
    recent_changes = (
        db.query(PriceHistory)
        .join(Product, Product.id == PriceHistory.product_id)
        .filter(
            Product.shop_id == shop_id,
            Product.is_deleted == False,
            Product.parent_id.is_(None),  # only real products, not parents
            PriceHistory.changed_at >= cutoff,
        )
        .order_by(PriceHistory.changed_at.desc())
        .all()
    )

    if not recent_changes:
        return []

    # Group by product_id
    by_product: dict[str, list] = {}
    for h in recent_changes:
        by_product.setdefault(h.product_id, []).append(h)

    # Fetch product details for products that had changes
    product_ids = list(by_product.keys())
    products = (
        db.query(Product)
        .filter(Product.id.in_(product_ids), Product.shop_id == shop_id)
        .all()
    )
    product_by_id = {p.id: p for p in products}

    # Build result
    result = []
    for pid, changes in by_product.items():
        p = product_by_id.get(pid)
        if not p:
            continue

        current_margin = None
        if p.selling_price and p.selling_price > 0:
            current_margin = round(
                (p.selling_price - (p.purchase_price or 0)) / p.selling_price * 100, 2
            )

        # Take top 5 most recent changes per product
        changes_out = []
        for h in changes[:5]:
            old = h.old_price or 0
            new = h.new_price or 0
            change_pct = round((new - old) / old * 100, 2) if old > 0 else None
            changes_out.append({
                "id": h.id,
                "price_type": h.price_type or "selling",
                "old_price": old,
                "new_price": new,
                "change_percent": change_pct,
                "changed_at": h.changed_at.isoformat() if h.changed_at else None,
            })

        result.append({
            "product": {
                "id": p.id,
                "name": p.name,
                "unit": p.unit,
                "current_selling_price": p.selling_price or 0,
                "current_purchase_price": p.purchase_price or 0,
                "current_margin_percent": current_margin,
            },
            "changes": changes_out,
            "_latest": changes[0].changed_at if changes else None,
        })

    # Sort by most recent change
    result.sort(key=lambda x: x["_latest"] or datetime.min, reverse=True)
    for r in result:
        del r["_latest"]

    return result[:limit]


# ─── Existing endpoints (unchanged) ───────────────────────────────


@router.get("/sell-speed")
def get_sell_speed(db: Session = Depends(get_db), shop_id: str = Depends(get_current_shop_id)):
    batches = db.query(StockBatch).filter(StockBatch.shop_id == shop_id).all()
    results = []

    for batch in batches:
        if batch.date_finished:
            days = (batch.date_finished - batch.date_added).days
            results.append({
                "product_id": batch.product_id,
                "quantity": batch.quantity_added,
                "days_to_sell": days,
            })

    return results


@router.get("/insights")
def insights(db: Session = Depends(get_db), shop_id: str = Depends(get_current_shop_id)):
    total_products = db.query(Product).filter(Product.shop_id == shop_id).count()
    total_sales = db.query(Sale).filter(Sale.shop_id == shop_id).count()

    return {
        "message": "Insights ready",
        "total_products": total_products,
        "total_sales": total_sales,
    }


@router.get("/revenue-trend")
def revenue_trend(db: Session = Depends(get_db), shop_id: str = Depends(get_current_shop_id)):
    """Return total revenue for each of the last 6 days (scoped to this shop)."""
    today = datetime.utcnow().date()
    six_days_ago = today - timedelta(days=5)

    results = []
    for i in range(6):
        day = six_days_ago + timedelta(days=i)
        next_day = day + timedelta(days=1)

        total = (
            db.query(func.sum(Sale.total_amount))
            .filter(Sale.shop_id == shop_id, Sale.created_at >= day, Sale.created_at < next_day)
            .scalar()
            or 0
        )

        results.append({"date": day.isoformat(), "revenue": float(total)})

    return results


@router.get("/top-products")
def top_products(
    period: str = "day", db: Session = Depends(get_db), shop_id: str = Depends(get_current_shop_id)
):
    """Return top 10 products by quantity sold in the given period."""
    return _compute_top_products(db, shop_id, period)


@router.get("/profit-margins")
def profit_margins(db: Session = Depends(get_db), shop_id: str = Depends(get_current_shop_id)):
    """Return profit margin for each product based on all sales."""
    return _compute_profit_margins(db, shop_id)


@router.get("/peak-hours")
def peak_hours(db: Session = Depends(get_db), shop_id: str = Depends(get_current_shop_id)):
    """Return sales count grouped by hour of day (0-23)."""
    return {"hours": _compute_peak_hours_array(db, shop_id)}


@router.get("/expense-breakdown")
def expense_breakdown(db: Session = Depends(get_db), shop_id: str = Depends(get_current_shop_id)):
    """Sum expenses grouped by category."""
    return _compute_expense_breakdown(db, shop_id)


# ─── NEW: Summary endpoint ────────────────────────────────────────


@router.get("/summary")
def analytics_summary(
    period: str = Query("day", description="day | week | month"),
    price_history_days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    """
    Combined analytics for the Insights page.

    Replaces 6+ individual API calls with one:
      - insights (counts)
      - top_products
      - profit_margins
      - peak_hours
      - expense_breakdown
      - recent_price_changes (removes N+1 loop from frontend)

    Use `period` to control the window for top-products (day/week/month).
    """
    if period not in ("day", "week", "month"):
        period = "day"

    total_products = db.query(Product).filter(Product.shop_id == shop_id).count()
    total_sales = db.query(Sale).filter(Sale.shop_id == shop_id).count()

    return {
        "period": period,
        "generated_at": datetime.utcnow().isoformat(),
        "counts": {
            "total_products": total_products,
            "total_sales": total_sales,
        },
        "top_products": _compute_top_products(db, shop_id, period),
        "profit_margins": _compute_profit_margins(db, shop_id),
        "peak_hours": _compute_peak_hours_array(db, shop_id),
        "expense_breakdown": _compute_expense_breakdown(db, shop_id),
        "recent_price_changes": _compute_recent_price_changes(
            db, shop_id, days=price_history_days, limit=5
        ),
    }