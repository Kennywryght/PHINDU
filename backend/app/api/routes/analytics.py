"""Analytics routes."""

from datetime import datetime, timedelta
from itertools import combinations

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

_IS_SQLITE = engine.url.drivername.startswith("sqlite")

_EXCLUDE_FROM_BASKET = {
    "plastic bag",
    "carrier bag",
    "polythene bag",
    "shopping bag",
}


def _period_start(period: str) -> datetime:
    now = datetime.utcnow()
    if period == "day":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "week":
        start = now - timedelta(days=now.weekday())
        return start.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "month":
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return now - timedelta(days=30)


def _compute_peak_hours_array(db: Session, shop_id: str) -> list[int]:
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
    now = datetime.utcnow()
    start_date = _period_start(period)

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


def _compute_top_products_with_parents(
    db: Session, shop_id: str, period: str, limit: int = 5
) -> list[dict]:
    now = datetime.utcnow()
    start_date = _period_start(period)

    results = (
        db.query(
            Product.id,
            Product.name,
            Product.category,
            Product.parent_id,
            func.sum(SaleItem.quantity).label("total_quantity"),
            func.sum(SaleItem.total_price).label("total_revenue"),
        )
        .join(SaleItem, SaleItem.product_id == Product.id)
        .join(Sale, Sale.id == SaleItem.sale_id)
        .filter(Sale.shop_id == shop_id, Sale.created_at >= start_date, Sale.created_at <= now)
        .group_by(Product.id, Product.name, Product.category, Product.parent_id)
        .order_by(func.sum(SaleItem.quantity).desc())
        .limit(limit)
        .all()
    )

    parent_ids = {r.parent_id for r in results if r.parent_id}
    parents_by_id: dict[str, str] = {}
    if parent_ids:
        for p in (
            db.query(Product.id, Product.name)
            .filter(Product.id.in_(parent_ids), Product.shop_id == shop_id)
            .all()
        ):
            parents_by_id[p.id] = p.name

    out = []
    for r in results:
        out.append({
            "id": r.id,
            "name": r.name,
            "category": r.category,
            "is_variant": r.parent_id is not None,
            "parent_id": r.parent_id,
            "parent_name": parents_by_id.get(r.parent_id) if r.parent_id else None,
            "quantity": float(r.total_quantity or 0),
            "revenue": float(r.total_revenue or 0),
        })
    return out


def _compute_category_performance(
    db: Session, shop_id: str, period: str
) -> list[dict]:
    now = datetime.utcnow()
    start_date = _period_start(period)

    results = (
        db.query(
            Product.category,
            func.sum(SaleItem.total_price).label("revenue"),
            func.sum(SaleItem.quantity).label("quantity"),
            func.count(func.distinct(Sale.id)).label("sale_count"),
        )
        .join(SaleItem, SaleItem.product_id == Product.id)
        .join(Sale, Sale.id == SaleItem.sale_id)
        .filter(Sale.shop_id == shop_id, Sale.created_at >= start_date, Sale.created_at <= now)
        .group_by(Product.category)
        .all()
    )

    rows = []
    total_revenue = 0.0
    for r in results:
        rev = float(r.revenue or 0)
        total_revenue += rev
        rows.append({
            "category": r.category or "Uncategorized",
            "revenue": round(rev, 2),
            "quantity": float(r.quantity or 0),
            "sale_count": int(r.sale_count or 0),
        })

    for row in rows:
        row["revenue_percent"] = (
            round((row["revenue"] / total_revenue) * 100, 1)
            if total_revenue > 0
            else 0.0
        )

    rows.sort(key=lambda x: x["revenue"], reverse=True)
    return rows


def _compute_profit_margins(db: Session, shop_id: str, period: str | None = None) -> list[dict]:
    query = (
        db.query(
            Product.id,
            Product.name,
            func.sum(SaleItem.total_price).label("revenue"),
            func.sum(SaleItem.cost_price).label("cost"),
        )
        .join(SaleItem, SaleItem.product_id == Product.id)
        .join(Sale, Sale.id == SaleItem.sale_id)
        .filter(Sale.shop_id == shop_id)
    )
    if period:
        now = datetime.utcnow()
        query = query.filter(Sale.created_at >= _period_start(period), Sale.created_at <= now)

    results = query.group_by(Product.id, Product.name).all()

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


def _compute_expense_breakdown(db: Session, shop_id: str, period: str | None = None) -> list[dict]:
    query = (
        db.query(Expense.category, func.sum(Expense.amount).label("total"))
        .filter(Expense.shop_id == shop_id)
    )
    if period:
        now = datetime.utcnow()
        query = query.filter(
            Expense.created_at >= _period_start(period), Expense.created_at <= now
        )
    results = query.group_by(Expense.category).all()
    rows = [{"category": r.category or "Uncategorized", "total": float(r.total or 0)} for r in results]
    rows.sort(key=lambda x: x["total"], reverse=True)
    return rows


def _compute_recent_price_changes(
    db: Session,
    shop_id: str,
    days: int = 30,
    limit: int = 30,
    include_variants: bool = True,
) -> list[dict]:
    cutoff = datetime.utcnow() - timedelta(days=days)

    q = (
        db.query(PriceHistory)
        .join(Product, Product.id == PriceHistory.product_id)
        .filter(
            Product.shop_id == shop_id,
            Product.is_deleted == False,
            PriceHistory.changed_at >= cutoff,
        )
    )
    if not include_variants:
        q = q.filter(Product.parent_id.is_(None))

    recent_changes = q.order_by(PriceHistory.changed_at.desc()).all()
    if not recent_changes:
        return []

    by_product: dict[str, list] = {}
    for h in recent_changes:
        by_product.setdefault(h.product_id, []).append(h)

    product_ids = list(by_product.keys())
    products = (
        db.query(Product)
        .filter(Product.id.in_(product_ids), Product.shop_id == shop_id)
        .all()
    )
    product_by_id = {p.id: p for p in products}

    parent_ids = {p.parent_id for p in products if p.parent_id}
    parents_by_id: dict[str, str] = {}
    if parent_ids:
        for parent in (
            db.query(Product.id, Product.name)
            .filter(Product.id.in_(parent_ids), Product.shop_id == shop_id)
            .all()
        ):
            parents_by_id[parent.id] = parent.name

    def _fmt(h):
        if h is None:
            return None
        old = h.old_price or 0
        new = h.new_price or 0
        change_pct = round((new - old) / old * 100, 2) if old > 0 else None
        return {
            "id": h.id,
            "old_price": old,
            "new_price": new,
            "change_percent": change_pct,
            "changed_at": h.changed_at.isoformat() if h.changed_at else None,
        }

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

        last_cost = next((c for c in changes if (c.price_type or "selling") == "purchase"), None)
        last_sell = next((c for c in changes if (c.price_type or "selling") == "selling"), None)

        candidates = [h.changed_at for h in (last_cost, last_sell) if h and h.changed_at]
        latest = max(candidates) if candidates else None

        all_changes = []
        for h in changes[:10]:
            old = h.old_price or 0
            new = h.new_price or 0
            change_pct = round((new - old) / old * 100, 2) if old > 0 else None
            all_changes.append({
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
                "category": p.category,
                "is_variant": p.parent_id is not None,
                "parent_name": parents_by_id.get(p.parent_id) if p.parent_id else None,
                "current_selling_price": p.selling_price or 0,
                "current_purchase_price": p.purchase_price or 0,
                "current_margin_percent": current_margin,
            },
            "last_cost_change": _fmt(last_cost),
            "last_sell_change": _fmt(last_sell),
            "changes": all_changes,
            "_latest": latest,
        })

    result.sort(key=lambda x: x["_latest"] or datetime.min, reverse=True)
    for r in result:
        del r["_latest"]

    return result[:limit]


def _compute_week_glance(db: Session, shop_id: str) -> dict:
    now = datetime.utcnow()
    cur_start = now - timedelta(days=7)
    prev_start = now - timedelta(days=14)

    def _metrics(start: datetime, end: datetime) -> dict:
        rev, cost = (
            db.query(
                func.coalesce(func.sum(SaleItem.total_price), 0),
                func.coalesce(func.sum(SaleItem.cost_price), 0),
            )
            .join(Sale, Sale.id == SaleItem.sale_id)
            .filter(
                Sale.shop_id == shop_id,
                Sale.created_at >= start,
                Sale.created_at < end,
                Sale.is_voided == False,
            )
            .one()
        )
        revenue = float(rev or 0)
        cogs = float(cost or 0)

        expenses = (
            db.query(func.coalesce(func.sum(Expense.amount), 0))
            .filter(
                Expense.shop_id == shop_id,
                Expense.created_at >= start,
                Expense.created_at < end,
            )
            .scalar()
            or 0
        )
        expenses = float(expenses or 0)

        sale_count = (
            db.query(func.count(Sale.id))
            .filter(
                Sale.shop_id == shop_id,
                Sale.created_at >= start,
                Sale.created_at < end,
                Sale.is_voided == False,
            )
            .scalar()
            or 0
        )

        profit = revenue - cogs - expenses
        avg_sale = (revenue / sale_count) if sale_count else 0.0

        return {
            "revenue": revenue,
            "profit": profit,
            "sales_count": int(sale_count),
            "avg_sale": avg_sale,
            "expenses": expenses,
        }

    cur = _metrics(cur_start, now)
    prev = _metrics(prev_start, cur_start)

    def _delta(cur_val: float, prev_val: float) -> dict:
        abs_d = cur_val - prev_val
        pct = None
        if prev_val != 0:
            pct = round((abs_d / prev_val) * 100, 1)
        elif cur_val > 0:
            pct = 100.0
        return {
            "current": round(cur_val, 2),
            "previous": round(prev_val, 2),
            "absolute": round(abs_d, 2),
            "percent": pct,
        }

    return {
        "revenue": _delta(cur["revenue"], prev["revenue"]),
        "profit": _delta(cur["profit"], prev["profit"]),
        "sales_count": _delta(cur["sales_count"], prev["sales_count"]),
        "avg_sale": _delta(cur["avg_sale"], prev["avg_sale"]),
        "expenses": _delta(cur["expenses"], prev["expenses"]),
    }


def _compute_low_stock(db: Session, shop_id: str, threshold: int = 5) -> list[dict]:
    results = (
        db.query(Product.id, Product.name, Product.category, Product.stock_qty)
        .filter(
            Product.shop_id == shop_id,
            Product.is_deleted == False,
            Product.archived == False,
            Product.stock_qty <= threshold,
        )
        .order_by(Product.stock_qty.asc())
        .limit(10)
        .all()
    )
    return [
        {
            "id": r.id,
            "name": r.name,
            "category": r.category,
            "stock_qty": float(r.stock_qty or 0),
        }
        for r in results
    ]


def _compute_market_basket(
    db: Session,
    shop_id: str,
    period: str = "month",
    min_support_count: int = 3,
    max_pairs: int = 15,
) -> dict:
    now = datetime.utcnow()
    start_date = _period_start(period) if period != "all" else None

    sale_q = (
        db.query(Sale.id, SaleItem.product_id)
        .join(SaleItem, SaleItem.sale_id == Sale.id)
        .filter(Sale.shop_id == shop_id, Sale.is_voided == False)
    )
    if start_date is not None:
        sale_q = sale_q.filter(Sale.created_at >= start_date, Sale.created_at <= now)

    baskets: dict[str, set[str]] = {}
    for sale_id, product_id in sale_q.all():
        if not product_id:
            continue
        baskets.setdefault(sale_id, set()).add(product_id)

    n_baskets = len(baskets)
    if n_baskets < 2:
        return {"baskets_analyzed": n_baskets, "pairs": []}

    item_count: dict[str, int] = {}
    pair_count: dict[tuple[str, str], int] = {}

    for items in baskets.values():
        if len(items) < 2:
            for pid in items:
                item_count[pid] = item_count.get(pid, 0) + 1
            continue
        for pid in items:
            item_count[pid] = item_count.get(pid, 0) + 1
        for a, b in combinations(sorted(items), 2):
            pair_count[(a, b)] = pair_count.get((a, b), 0) + 1

    candidates = [
        (a, b, c) for (a, b), c in pair_count.items() if c >= min_support_count
    ]
    if not candidates:
        return {"baskets_analyzed": n_baskets, "pairs": []}

    all_ids = {pid for a, b, _ in candidates for pid in (a, b)}
    products = (
        db.query(Product.id, Product.name, Product.category)
        .filter(Product.id.in_(all_ids), Product.shop_id == shop_id)
        .all()
    )
    prod_by_id = {p.id: p for p in products}

    def _is_excluded(p) -> bool:
        return (p.name or "").strip().lower() in _EXCLUDE_FROM_BASKET

    results = []
    for a, b, co in candidates:
        pa = prod_by_id.get(a)
        pb = prod_by_id.get(b)
        if not pa or not pb:
            continue
        if _is_excluded(pa) or _is_excluded(pb):
            continue

        sup_a = item_count[a] / n_baskets
        sup_b = item_count[b] / n_baskets
        sup_ab = co / n_baskets

        conf_ab = co / item_count[a] if item_count[a] else 0.0
        conf_ba = co / item_count[b] if item_count[b] else 0.0
        lift = conf_ab / sup_b if sup_b > 0 else 0.0

        score = lift * conf_ab * (1.0 + sup_ab * 10)

        results.append({
            "product_a": {"id": pa.id, "name": pa.name, "category": pa.category},
            "product_b": {"id": pb.id, "name": pb.name, "category": pb.category},
            "co_count": co,
            "support_a": round(sup_a, 4),
            "support_b": round(sup_b, 4),
            "support_pair": round(sup_ab, 4),
            "confidence_ab": round(conf_ab, 4),
            "confidence_ba": round(conf_ba, 4),
            "lift": round(lift, 2),
            "_score": score,
        })

    results.sort(key=lambda r: r["_score"], reverse=True)
    for r in results:
        del r["_score"]

    return {"baskets_analyzed": n_baskets, "pairs": results[:max_pairs]}


# ─── Endpoints ────────────────────────────────────────────────────


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
def revenue_trend(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    today = datetime.utcnow().date()
    start_day = today - timedelta(days=days - 1)
    results = []
    for i in range(days):
        day = start_day + timedelta(days=i)
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
    return _compute_top_products(db, shop_id, period)


@router.get("/profit-margins")
def profit_margins(db: Session = Depends(get_db), shop_id: str = Depends(get_current_shop_id)):
    return _compute_profit_margins(db, shop_id)


@router.get("/peak-hours")
def peak_hours(db: Session = Depends(get_db), shop_id: str = Depends(get_current_shop_id)):
    return {"hours": _compute_peak_hours_array(db, shop_id)}


@router.get("/expense-breakdown")
def expense_breakdown(db: Session = Depends(get_db), shop_id: str = Depends(get_current_shop_id)):
    return _compute_expense_breakdown(db, shop_id)


@router.get("/price-changes")
def price_changes(
    days: int | None = Query(30, ge=1, le=365),
    limit: int = Query(30, ge=1, le=200),
    include_variants: bool = Query(True),
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    lookback = days if days is not None else 36500
    return _compute_recent_price_changes(
        db,
        shop_id,
        days=lookback,
        limit=limit,
        include_variants=include_variants,
    )


@router.get("/market-basket")
def market_basket(
    period: str = Query("month"),
    min_support: int = Query(3, ge=1, le=50),
    limit: int = Query(15, ge=1, le=50),
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    if period not in ("day", "week", "month", "all"):
        period = "month"
    return _compute_market_basket(
        db, shop_id, period=period, min_support_count=min_support, max_pairs=limit
    )


@router.get("/summary")
def analytics_summary(
    period: str = Query("day"),
    price_history_days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    if period not in ("day", "week", "month"):
        period = "day"

    total_products = db.query(Product).filter(Product.shop_id == shop_id).count()
    total_sales = db.query(Sale).filter(Sale.shop_id == shop_id).count()

    week_glance = _compute_week_glance(db, shop_id)
    week_expenses = week_glance.get("expenses", {}).get("current", 0.0)

    return {
        "period": period,
        "generated_at": datetime.utcnow().isoformat(),
        "counts": {
            "total_products": total_products,
            "total_sales": total_sales,
        },
        "top_products": _compute_top_products(db, shop_id, period),
        "top_products_detailed": _compute_top_products_with_parents(db, shop_id, period),
        "category_performance": _compute_category_performance(db, shop_id, period),
        "profit_margins": _compute_profit_margins(db, shop_id, period),
        "peak_hours": _compute_peak_hours_array(db, shop_id),
        "expense_breakdown": _compute_expense_breakdown(db, shop_id, period),
        "recent_price_changes": _compute_recent_price_changes(
            db, shop_id, days=price_history_days, limit=30, include_variants=True
        ),
        "recent_price_changes_v2": _compute_recent_price_changes(
            db, shop_id, days=price_history_days, limit=30, include_variants=True
        ),
        "week_glance": week_glance,
        "week_expenses": round(float(week_expenses or 0), 2),
        "low_stock": _compute_low_stock(db, shop_id, threshold=5),
        "market_basket": _compute_market_basket(db, shop_id, period="month", max_pairs=10),
    }