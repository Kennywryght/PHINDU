"""Dashboard routes: summary + today + health score + focus + cash flow + deltas + sparklines
+ alerts + top customers + debt ageing + slow movers + heatmap + sessions trend."""

from datetime import datetime, timedelta, date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, exists, func
from sqlalchemy.orm import Session, aliased

from app.api.dependencies import get_current_shop_id
from app.db.models.customer import Customer
from app.db.models.expense import Expense
from app.db.models.payment import Payment
from app.db.models.price_history import PriceHistory
from app.db.models.product import Product
from app.db.models.sale import Sale, SaleItem
from app.db.models.session import Session as SessionModel
from app.db.models.stock import StockBatch
from app.db.session import get_db

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


# ─── Helpers ─────────────────────────────────────────────────────


def _today_utc_range():
    now = datetime.utcnow()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start + timedelta(days=1)


def _leaf_products_query(db: Session, shop_id: str):
    """
    Base query for LEAF products (products with NO child variants).

    Standalone products AND parent-with-variants products both have
    parent_id IS NULL — the only reliable way to detect leaves is a
    "no children exist" check.
    """
    child = aliased(Product)
    return (
        db.query(Product)
        .filter(
            Product.shop_id == shop_id,
            Product.is_deleted == False,
            Product.archived == False,
            ~exists().where(
                and_(
                    child.parent_id == Product.id,
                    child.shop_id == shop_id,
                    child.is_deleted == False,
                )
            ),
        )
    )


def _low_stock_count(db: Session, shop_id: str) -> int:
    child = aliased(Product)
    return (
        db.query(func.count(Product.id))
        .filter(
            Product.shop_id == shop_id,
            Product.is_deleted == False,
            Product.archived == False,
            Product.stock_qty <= Product.low_stock_threshold,
            ~exists().where(
                and_(
                    child.parent_id == Product.id,
                    child.shop_id == shop_id,
                    child.is_deleted == False,
                )
            ),
        )
        .scalar()
        or 0
    )


def _leaf_product_count(db: Session, shop_id: str) -> int:
    child = aliased(Product)
    return (
        db.query(func.count(Product.id))
        .filter(
            Product.shop_id == shop_id,
            Product.is_deleted == False,
            Product.archived == False,
            ~exists().where(
                and_(
                    child.parent_id == Product.id,
                    child.shop_id == shop_id,
                    child.is_deleted == False,
                )
            ),
        )
        .scalar()
        or 0
    )


def _revenue_and_profit_for_window(db: Session, shop_id: str, start: datetime, end: datetime) -> dict:
    revenue, cost = (
        db.query(
            func.coalesce(func.sum(SaleItem.total_price), 0),
            func.coalesce(func.sum(SaleItem.cost_price), 0),
        )
        .join(Sale, Sale.id == SaleItem.sale_id)
        .filter(Sale.shop_id == shop_id, Sale.created_at >= start, Sale.created_at < end)
        .one()
    )
    revenue = float(revenue or 0)
    cost = float(cost or 0)

    expenses = (
        db.query(func.coalesce(func.sum(Expense.amount), 0))
        .filter(Expense.shop_id == shop_id, Expense.created_at >= start, Expense.created_at < end)
        .scalar()
        or 0
    )
    expenses = float(expenses or 0)

    return {
        "revenue": revenue,
        "cost": cost,
        "expenses": expenses,
        "profit": revenue - cost - expenses,
    }


def _sales_count_for_window(db: Session, shop_id: str, start: datetime, end: datetime) -> int:
    return (
        db.query(func.count(Sale.id))
        .filter(Sale.shop_id == shop_id, Sale.created_at >= start, Sale.created_at < end)
        .scalar()
        or 0
    )


# ─── GET / (existing summary) ───────────────────────────────────


@router.get("/")
def get_dashboard(
    session_id: str = Query(None),
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    if not session_id:
        active_session = (
            db.query(SessionModel)
            .filter(
                SessionModel.is_active == True,
                SessionModel.shop_id == shop_id,
            )
            .first()
        )
        if active_session:
            session_id = active_session.id

    sale_items_query = db.query(SaleItem).join(Sale).filter(Sale.shop_id == shop_id)
    if session_id:
        sale_items_query = sale_items_query.filter(Sale.session_id == session_id)

    items = sale_items_query.all()

    total_revenue = 0.0
    total_cost = 0.0
    total_quantity = 0
    product_sales = {}

    for item in items:
        total_revenue += item.total_price
        total_cost += item.cost_price or 0
        total_quantity += item.quantity
        product_sales[item.product_id] = product_sales.get(item.product_id, 0) + item.quantity

    expenses_query = db.query(func.sum(Expense.amount)).filter(Expense.shop_id == shop_id)
    if session_id:
        expenses_query = expenses_query.filter(Expense.session_id == session_id)
    total_expenses = expenses_query.scalar() or 0.0

    profit = total_revenue - total_cost - total_expenses

    top_products = sorted(product_sales.items(), key=lambda x: x[1], reverse=True)[:5]

    best_product_id = max(product_sales, key=product_sales.get) if product_sales else None
    worst_product_id = min(product_sales, key=product_sales.get) if product_sales else None

    def _name_of(pid):
        if not pid:
            return None
        p = db.query(Product).filter(Product.id == pid).first()
        return p.name if p else None

    best_product = _name_of(best_product_id)
    worst_product = _name_of(worst_product_id)

    avg_item_price = (total_revenue / total_quantity) if total_quantity else 0.0
    profit_margin = (profit / total_revenue * 100) if total_revenue else 0.0

    return {
        "session_id": session_id,
        "total_revenue": total_revenue,
        "total_cost": total_cost,
        "profit": profit,
        "total_items_sold": total_quantity,
        "top_products": top_products,
        "best_product": best_product,
        "worst_product": worst_product,
        "avg_sale_value": avg_item_price,
        "profit_margin": profit_margin,
        "total_expenses": total_expenses,
    }


# ─── GET /today ─────────────────────────────────────────────────


@router.get("/today")
def get_today_snapshot(
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    start, end = _today_utc_range()
    financials = _revenue_and_profit_for_window(db, shop_id, start, end)
    sales_count = _sales_count_for_window(db, shop_id, start, end)
    low_stock = _low_stock_count(db, shop_id)

    return {
        "date": start.date().isoformat(),
        "revenue": round(financials["revenue"], 2),
        "profit": round(financials["profit"], 2),
        "sales_count": sales_count,
        "low_stock_count": low_stock,
    }


# ─── GET /health-score ──────────────────────────────────────────


@router.get("/health-score")
def get_health_score(
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    now = datetime.utcnow()

    cur_start = now - timedelta(days=7)
    cur_fin = _revenue_and_profit_for_window(db, shop_id, cur_start, now)

    prev_start = now - timedelta(days=14)
    prev_end = cur_start
    prev_fin = _revenue_and_profit_for_window(db, shop_id, prev_start, prev_end)

    def _score_for(fin: dict) -> tuple[int, dict]:
        score = 0
        components = {}

        revenue = fin["revenue"]
        profit = fin["profit"]

        # Profit margin (max 40)
        if revenue > 0:
            margin = profit / revenue
        else:
            margin = 0.0
        if margin >= 0.30:
            pm_points = 40
        elif margin >= 0.15:
            pm_points = 25
        elif margin > 0:
            pm_points = 10
        else:
            pm_points = 0
        components["profit_margin_points"] = pm_points
        components["profit_margin_pct"] = round(margin * 100, 1)
        score += pm_points

        # Cash flow (max 30)
        if revenue > 0:
            cf_ratio = max(0.0, min(1.0, profit / revenue))
        else:
            cf_ratio = 0.0
        cf_points = int(round(cf_ratio * 30))
        components["cash_flow_points"] = cf_points
        components["cash_flow_ratio"] = round(cf_ratio, 2)
        score += cf_points

        # Stock health (max 20) — leaf products only
        leaf_total = _leaf_product_count(db, shop_id)
        low = _low_stock_count(db, shop_id)
        if leaf_total > 0:
            healthy_ratio = max(0.0, 1.0 - (low / leaf_total))
        else:
            healthy_ratio = 1.0
        stock_points = int(round(healthy_ratio * 20))
        components["stock_points"] = stock_points
        components["healthy_products"] = leaf_total - low
        components["total_products"] = leaf_total
        components["low_stock"] = low
        score += stock_points

        # Debt collection (max 10)
        collected = (
            db.query(func.coalesce(func.sum(Payment.amount), 0))
            .filter(
                Payment.shop_id == shop_id,
                Payment.created_at >= cur_start,
                Payment.created_at <= now,
            )
            .scalar()
            or 0
        )
        invoiced = (
            db.query(func.coalesce(func.sum(Sale.total_amount), 0))
            .filter(
                Sale.shop_id == shop_id,
                Sale.created_at >= cur_start,
                Sale.created_at <= now,
                Sale.payment_status.in_(["unpaid", "partial"]),
            )
            .scalar()
            or 0
        )
        if invoiced > 0:
            collect_ratio = min(1.0, float(collected) / float(invoiced))
        else:
            collect_ratio = 1.0
        debt_points = int(round(collect_ratio * 10))
        components["debt_points"] = debt_points
        components["collection_ratio"] = round(collect_ratio, 2)
        score += debt_points

        return max(0, min(100, score)), components

    score, components = _score_for(cur_fin)
    prev_score, _ = _score_for(prev_fin)
    delta = score - prev_score

    if score >= 70:
        tone, label = "good", "Healthy"
        message = "You're doing well — keep it up."
    elif score >= 40:
        tone, label = "warn", "Watch"
        message = "Mixed signals — check profit margin and stock."
    else:
        tone, label = "bad", "Needs attention"
        message = "Several areas need attention this week."

    return {
        "score": score,
        "previous": prev_score,
        "delta": delta,
        "tone": tone,
        "label": label,
        "message": message,
        "components": components,
        "window": {
            "start": cur_start.isoformat(),
            "end": now.isoformat(),
            "previous_start": prev_start.isoformat(),
            "previous_end": prev_end.isoformat(),
        },
    }


# ─── GET /focus ─────────────────────────────────────────────────


@router.get("/focus")
def get_focus_actions(
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    items: list[dict] = []
    now = datetime.utcnow()
    cutoff_30d = now - timedelta(days=30)
    cutoff_14d = now - timedelta(days=14)

    # Precompute recent sales map
    sold_recently = (
        db.query(
            SaleItem.product_id,
            func.sum(SaleItem.quantity).label("sold"),
        )
        .join(Sale, Sale.id == SaleItem.sale_id)
        .filter(Sale.shop_id == shop_id, Sale.created_at >= cutoff_30d)
        .group_by(SaleItem.product_id)
        .all()
    )
    sold_map = {row.product_id: float(row.sold or 0) for row in sold_recently}

    # ── 1. Critical: zero stock but sold recently ──
    zero_stock = (
        _leaf_products_query(db, shop_id)
        .filter(Product.stock_qty <= 0)
        .all()
    )
    for p in zero_stock:
        if sold_map.get(p.id, 0) > 0:
            items.append({
                "type": "critical",
                "severity": "high",
                "title": f"{p.name} is out of stock",
                "detail": f"Sold {int(sold_map[p.id])} {p.unit or 'units'} in last 30 days",
                "hint": "Restock now",
                "link": f"/products/{p.id}",
            })
            if len(items) >= 3:
                return {"generated_at": now.isoformat(), "items": items}

    # ── 2. Restock: < 3 days of stock ──
    live_products = (
        _leaf_products_query(db, shop_id)
        .filter(Product.stock_qty > 0)
        .all()
    )
    restock_candidates = []
    for p in live_products:
        sold = sold_map.get(p.id, 0)
        if sold <= 0:
            continue
        daily = sold / 30.0
        if daily <= 0:
            continue
        days_left = (p.stock_qty or 0) / daily
        if days_left < 3:
            restock_candidates.append((days_left, p, daily))
    restock_candidates.sort(key=lambda x: x[0])
    for days_left, p, daily in restock_candidates:
        items.append({
            "type": "restock",
            "severity": "high",
            "title": f"{p.name} — ~{days_left:.1f} days of stock left",
            "detail": f"Current stock {int(p.stock_qty or 0)} {p.unit or 'units'} · ~{daily:.1f}/day",
            "hint": f"Order ~{max(1, int(round(daily * 7)))} {p.unit or 'units'} for a week",
            "link": f"/products/{p.id}",
        })
        if len(items) >= 3:
            return {"generated_at": now.isoformat(), "items": items}

    # ── 3. Debtors overdue >14 days ──
    overdue_customers = (
        db.query(Customer)
        .filter(Customer.shop_id == shop_id, Customer.total_credit > 0)
        .all()
    )
    overdue_total = 0.0
    overdue_count = 0
    for c in overdue_customers:
        last_payment = (
            db.query(func.max(Payment.created_at))
            .filter(Payment.customer_id == c.id, Payment.shop_id == shop_id)
            .scalar()
        )
        if last_payment is None or last_payment < cutoff_14d:
            overdue_total += float(c.total_credit or 0)
            overdue_count += 1

    if overdue_count > 0:
        items.append({
            "type": "debtors",
            "severity": "medium",
            "title": f"{overdue_count} debtor{'s' if overdue_count != 1 else ''} overdue 14+ days",
            "detail": f"MWK {overdue_total:,.0f} outstanding",
            "hint": "Review credit page",
            "link": "/credit",
        })
        if len(items) >= 3:
            return {"generated_at": now.isoformat(), "items": items}

    # ── 4. Margin drop (≥8 pts) in last 30 days ──
    leaf_products = _leaf_products_query(db, shop_id).filter(Product.selling_price > 0).all()
    margin_drops = []
    for p in leaf_products:
        recent_purchase_up = (
            db.query(PriceHistory)
            .filter(
                PriceHistory.product_id == p.id,
                PriceHistory.price_type == "purchase",
                PriceHistory.changed_at >= cutoff_30d,
                PriceHistory.new_price > PriceHistory.old_price,
            )
            .order_by(PriceHistory.changed_at.desc())
            .first()
        )
        if not recent_purchase_up:
            continue
        old_pp = float(recent_purchase_up.old_price or 0)
        new_pp = float(recent_purchase_up.new_price or 0)
        sp = float(p.selling_price or 0)
        if old_pp <= 0 or sp <= 0:
            continue
        old_margin = (sp - old_pp) / sp * 100
        new_margin = (sp - new_pp) / sp * 100
        drop = old_margin - new_margin
        if drop >= 8:
            margin_drops.append((drop, p, old_margin, new_margin))

    margin_drops.sort(key=lambda x: x[0], reverse=True)
    for drop, p, old_m, new_m in margin_drops:
        items.append({
            "type": "margin",
            "severity": "medium",
            "title": f"{p.name} margin dropped {drop:.1f} points",
            "detail": f"{old_m:.1f}% → {new_m:.1f}% (cost up, price flat)",
            "hint": "Consider raising price",
            "link": f"/products/{p.id}",
        })
        if len(items) >= 3:
            return {"generated_at": now.isoformat(), "items": items}

    # ── 5. Fallback: low-stock leaf products ──
    low_products = (
        _leaf_products_query(db, shop_id)
        .filter(Product.stock_qty > 0, Product.stock_qty <= Product.low_stock_threshold)
        .order_by(Product.stock_qty.asc())
        .limit(3 - len(items))
        .all()
    )
    for p in low_products:
        items.append({
            "type": "low_stock",
            "severity": "low",
            "title": f"{p.name} running low",
            "detail": f"{int(p.stock_qty or 0)} {p.unit or 'units'} left (threshold {int(p.low_stock_threshold or 0)})",
            "hint": "Restock soon",
            "link": f"/products/{p.id}",
        })

    return {"generated_at": now.isoformat(), "items": items[:3]}


# ─── GET /cash-flow ─────────────────────────────────────────────


@router.get("/cash-flow")
def get_cash_flow(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    now = datetime.utcnow()
    start = now - timedelta(days=days)

    sales_paid = (
        db.query(func.coalesce(func.sum(Sale.amount_paid), 0))
        .filter(
            Sale.shop_id == shop_id,
            Sale.created_at >= start,
            Sale.created_at <= now,
            Sale.is_voided == False,
        )
        .scalar()
        or 0
    )
    customer_payments = (
        db.query(func.coalesce(func.sum(Payment.amount), 0))
        .filter(
            Payment.shop_id == shop_id,
            Payment.created_at >= start,
            Payment.created_at <= now,
        )
        .scalar()
        or 0
    )

    expenses_out = (
        db.query(func.coalesce(func.sum(Expense.amount), 0))
        .filter(
            Expense.shop_id == shop_id,
            Expense.created_at >= start,
            Expense.created_at <= now,
        )
        .scalar()
        or 0
    )
    stock_out = (
        db.query(func.coalesce(func.sum(StockBatch.quantity_added * StockBatch.cost_per_unit), 0))
        .filter(
            StockBatch.shop_id == shop_id,
            StockBatch.date_added >= start,
            StockBatch.date_added <= now,
            StockBatch.cost_per_unit.isnot(None),
        )
        .scalar()
        or 0
    )

    cash_in = float(sales_paid) + float(customer_payments)
    cash_out = float(expenses_out) + float(stock_out)
    net = cash_in - cash_out

    active_session = (
        db.query(SessionModel)
        .filter(SessionModel.is_active == True, SessionModel.shop_id == shop_id)
        .first()
    )
    if active_session:
        drawer = (
            db.query(func.coalesce(func.sum(Sale.amount_paid), 0))
            .filter(
                Sale.shop_id == shop_id,
                Sale.session_id == active_session.id,
                Sale.is_voided == False,
            )
            .scalar()
            or 0
        )
        drawer = float(drawer)
    else:
        drawer = None

    return {
        "window_days": days,
        "cash_in": round(cash_in, 2),
        "cash_out": round(cash_out, 2),
        "net": round(net, 2),
        "breakdown": {
            "sales_paid": round(float(sales_paid), 2),
            "customer_payments": round(float(customer_payments), 2),
            "expenses": round(float(expenses_out), 2),
            "stock_purchases": round(float(stock_out), 2),
        },
        "drawer": round(drawer, 2) if drawer is not None else None,
        "session_id": active_session.id if active_session else None,
    }


# ─── GET /metric-deltas ─────────────────────────────────────────


@router.get("/metric-deltas")
def get_metric_deltas(
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today_start + timedelta(days=1)
    yest_start = today_start - timedelta(days=1)

    def _metrics(a: datetime, b: datetime) -> dict:
        fin = _revenue_and_profit_for_window(db, shop_id, a, b)
        qty = (
            db.query(func.coalesce(func.sum(SaleItem.quantity), 0))
            .join(Sale, Sale.id == SaleItem.sale_id)
            .filter(Sale.shop_id == shop_id, Sale.created_at >= a, Sale.created_at < b)
            .scalar()
            or 0
        )
        return {
            "revenue": fin["revenue"],
            "profit": fin["profit"],
            "expenses": fin["expenses"],
            "items_sold": float(qty),
        }

    t = _metrics(today_start, tomorrow)
    y = _metrics(yest_start, today_start)

    def _delta(cur, prev):
        abs_d = cur - prev
        pct = None
        if prev != 0:
            pct = round((abs_d / prev) * 100, 1)
        elif cur > 0:
            pct = 100.0
        return {
            "current": round(cur, 2),
            "previous": round(prev, 2),
            "absolute": round(abs_d, 2),
            "percent": pct,
        }

    return {
        "revenue": _delta(t["revenue"], y["revenue"]),
        "profit": _delta(t["profit"], y["profit"]),
        "expenses": _delta(t["expenses"], y["expenses"]),
        "items_sold": _delta(t["items_sold"], y["items_sold"]),
    }


# ─── GET /top-products-trend ────────────────────────────────────


@router.get("/top-products-trend")
def get_top_products_trend(
    days: int = Query(7, ge=1, le=30),
    limit: int = Query(3, ge=1, le=10),
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    now = datetime.utcnow()
    start = (now - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)

    rows = (
        db.query(
            Product.id,
            Product.name,
            func.sum(SaleItem.quantity).label("qty"),
            func.sum(SaleItem.total_price).label("rev"),
        )
        .join(SaleItem, SaleItem.product_id == Product.id)
        .join(Sale, Sale.id == SaleItem.sale_id)
        .filter(
            Sale.shop_id == shop_id,
            Sale.created_at >= start,
            Sale.created_at <= now,
        )
        .group_by(Product.id, Product.name)
        .order_by(func.sum(SaleItem.quantity).desc())
        .limit(limit)
        .all()
    )

    results = []
    for row in rows:
        daily = (
            db.query(
                func.date(Sale.created_at).label("day"),
                func.sum(SaleItem.quantity).label("qty"),
            )
            .join(SaleItem, SaleItem.sale_id == Sale.id)
            .filter(
                Sale.shop_id == shop_id,
                SaleItem.product_id == row.id,
                Sale.created_at >= start,
                Sale.created_at <= now,
            )
            .group_by(func.date(Sale.created_at))
            .all()
        )
        daily_map = {str(r.day): float(r.qty or 0) for r in daily}

        sparkline = []
        for i in range(days):
            day = (start + timedelta(days=i)).date().isoformat()
            sparkline.append(daily_map.get(day, 0.0))

        results.append({
            "id": row.id,
            "name": row.name,
            "quantity": float(row.qty or 0),
            "revenue": round(float(row.rev or 0), 2),
            "sparkline": sparkline,
        })

    return {"window_days": days, "products": results}


# ─── GET /alerts ────────────────────────────────────────────────


@router.get("/alerts")
def get_alerts(
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    """
    Aggregated alert chips for the dashboard top strip.

    Each chip: { id, severity ('high'|'medium'|'low'|'info'),
                title, detail, link, cta }
    """
    now = datetime.utcnow()
    alerts: list[dict] = []

    # 1. No open session?
    active_session = (
        db.query(SessionModel)
        .filter(SessionModel.is_active == True, SessionModel.shop_id == shop_id)
        .first()
    )
    if not active_session:
        alerts.append({
            "id": "no_session",
            "severity": "info",
            "title": "No session open",
            "detail": "Sales won't be tracked until you open a session.",
            "link": "/sessions",
            "cta": "Open session",
        })

    # 2. Low stock
    low_stock_count = _low_stock_count(db, shop_id)
    if low_stock_count > 0:
        alerts.append({
            "id": "low_stock",
            "severity": "high" if low_stock_count >= 5 else "medium",
            "title": f"{low_stock_count} product{'s' if low_stock_count != 1 else ''} low on stock",
            "detail": "Restock to avoid losing sales.",
            "link": "/products?filter=low_stock",
            "cta": "View",
        })

    # 3. Zero-stock products that sold recently (critical)
    cutoff_30d = now - timedelta(days=30)
    sold_recently = (
        db.query(SaleItem.product_id)
        .join(Sale, Sale.id == SaleItem.sale_id)
        .filter(Sale.shop_id == shop_id, Sale.created_at >= cutoff_30d)
        .distinct()
        .subquery()
    )
    zero_stock_sold = (
        _leaf_products_query(db, shop_id)
        .filter(Product.stock_qty <= 0, Product.id.in_(sold_recently))
        .count()
    )
    if zero_stock_sold > 0:
        alerts.append({
            "id": "zero_stock",
            "severity": "high",
            "title": f"{zero_stock_sold} fast-mover{'s' if zero_stock_sold != 1 else ''} out of stock",
            "detail": "These products sold in the last 30 days but have 0 stock.",
            "link": "/products?filter=out_of_stock",
            "cta": "Restock",
        })

    # 4. Overdue debtors (14+ days no payment)
    cutoff_14d = now - timedelta(days=14)
    debtors = (
        db.query(Customer)
        .filter(Customer.shop_id == shop_id, Customer.total_credit > 0)
        .all()
    )
    overdue_count = 0
    overdue_total = 0.0
    for c in debtors:
        last_payment = (
            db.query(func.max(Payment.created_at))
            .filter(Payment.customer_id == c.id, Payment.shop_id == shop_id)
            .scalar()
        )
        if last_payment is None or last_payment < cutoff_14d:
            overdue_count += 1
            overdue_total += float(c.total_credit or 0)
    if overdue_count > 0:
        alerts.append({
            "id": "overdue_debt",
            "severity": "high" if overdue_count >= 3 else "medium",
            "title": f"{overdue_count} debtor{'s' if overdue_count != 1 else ''} overdue 14+ days",
            "detail": f"MWK {overdue_total:,.0f} outstanding.",
            "link": "/credit",
            "cta": "Follow up",
        })

    # 5. Revenue down vs last week
    cur_start = now - timedelta(days=7)
    prev_start = now - timedelta(days=14)
    cur = _revenue_and_profit_for_window(db, shop_id, cur_start, now)
    prev = _revenue_and_profit_for_window(db, shop_id, prev_start, cur_start)
    if prev["revenue"] > 0:
        pct = (cur["revenue"] - prev["revenue"]) / prev["revenue"] * 100
        if pct <= -15:
            alerts.append({
                "id": "revenue_down",
                "severity": "medium",
                "title": f"Revenue down {abs(pct):.0f}% vs last week",
                "detail": f"MWK {cur['revenue']:,.0f} this week vs MWK {prev['revenue']:,.0f} last week.",
                "link": "/insights",
                "cta": "Investigate",
            })

    if not alerts:
        alerts.append({
            "id": "all_good",
            "severity": "low",
            "title": "Everything looks good",
            "detail": "No urgent issues detected.",
            "link": None,
            "cta": None,
        })

    return {"generated_at": now.isoformat(), "alerts": alerts}


# ─── GET /top-customers ─────────────────────────────────────────


@router.get("/top-customers")
def get_top_customers(
    days: int = Query(7, ge=1, le=90),
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    """
    Top customers by revenue in the given window.

    Returns: [{ id, name, phone, revenue, purchase_count, credit_outstanding }]
    """
    now = datetime.utcnow()
    start = now - timedelta(days=days)

    rows = (
        db.query(
            Customer.id,
            Customer.name,
            Customer.phone,
            Customer.total_credit,
            func.coalesce(func.sum(Sale.total_amount), 0).label("revenue"),
            func.count(Sale.id).label("purchase_count"),
        )
        .join(Sale, Sale.customer_id == Customer.id)
        .filter(
            Customer.shop_id == shop_id,
            Sale.shop_id == shop_id,
            Sale.created_at >= start,
            Sale.created_at <= now,
            Sale.is_voided == False,
        )
        .group_by(Customer.id, Customer.name, Customer.phone, Customer.total_credit)
        .order_by(func.sum(Sale.total_amount).desc())
        .limit(limit)
        .all()
    )

    return {
        "window_days": days,
        "customers": [
            {
                "id": r.id,
                "name": r.name,
                "phone": r.phone,
                "revenue": round(float(r.revenue or 0), 2),
                "purchase_count": int(r.purchase_count or 0),
                "credit_outstanding": round(float(r.total_credit or 0), 2),
            }
            for r in rows
        ],
    }


# ─── GET /debt-ageing ───────────────────────────────────────────


@router.get("/debt-ageing")
def get_debt_ageing(
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    """
    Bucket outstanding customer credit by age of the oldest unpaid sale.

    A customer's whole `total_credit` is bucketed by the age of the oldest
    unpaid/partial sale they have.

    Buckets: current (<7d), 7-14d, 15-30d, over 30d.
    """
    now = datetime.utcnow()

    customers = (
        db.query(Customer)
        .filter(Customer.shop_id == shop_id, Customer.total_credit > 0)
        .all()
    )

    buckets = {
        "current": {"count": 0, "total": 0.0},
        "days_7_14": {"count": 0, "total": 0.0},
        "days_15_30": {"count": 0, "total": 0.0},
        "over_30": {"count": 0, "total": 0.0},
    }

    for c in customers:
        oldest = (
            db.query(func.min(Sale.created_at))
            .filter(
                Sale.customer_id == c.id,
                Sale.shop_id == shop_id,
                Sale.payment_status.in_(["unpaid", "partial"]),
                Sale.is_voided == False,
            )
            .scalar()
        )
        if not oldest:
            bucket = "current"
        else:
            age_days = (now - oldest).days
            if age_days < 7:
                bucket = "current"
            elif age_days < 15:
                bucket = "days_7_14"
            elif age_days < 31:
                bucket = "days_15_30"
            else:
                bucket = "over_30"

        buckets[bucket]["count"] += 1
        buckets[bucket]["total"] += float(c.total_credit or 0)

    for k in buckets:
        buckets[k]["total"] = round(buckets[k]["total"], 2)

    total = round(sum(b["total"] for b in buckets.values()), 2)
    return {"generated_at": now.isoformat(), "total": total, "buckets": buckets}


# ─── GET /slow-movers ───────────────────────────────────────────


@router.get("/slow-movers")
def get_slow_movers(
    days: int = Query(30, ge=7, le=180),
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    """
    Products with stock on hand but very few / zero sales in the window.

    Ranked by (stock_qty × purchase_price) descending — i.e. how much
    cash is sitting idle.
    """
    now = datetime.utcnow()
    start = now - timedelta(days=days)

    sold_map = {
        row.product_id: float(row.sold or 0)
        for row in (
            db.query(
                SaleItem.product_id,
                func.sum(SaleItem.quantity).label("sold"),
            )
            .join(Sale, Sale.id == SaleItem.sale_id)
            .filter(
                Sale.shop_id == shop_id,
                Sale.created_at >= start,
                Sale.is_voided == False,
            )
            .group_by(SaleItem.product_id)
            .all()
        )
    }

    candidates = (
        _leaf_products_query(db, shop_id)
        .filter(Product.stock_qty > 0)
        .all()
    )

    rows = []
    for p in candidates:
        sold = sold_map.get(p.id, 0.0)
        if sold > 2:
            continue
        idle_value = float(p.stock_qty or 0) * float(p.purchase_price or 0)
        rows.append({
            "id": p.id,
            "name": p.name,
            "category": p.category,
            "stock_qty": float(p.stock_qty or 0),
            "unit": p.unit,
            "sold": sold,
            "idle_value": round(idle_value, 2),
        })

    rows.sort(key=lambda r: r["idle_value"], reverse=True)
    return {"window_days": days, "products": rows[:limit]}


# ─── GET /heatmap ───────────────────────────────────────────────


@router.get("/heatmap")
def get_heatmap(
    days: int = Query(30, ge=7, le=180),
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    """
    7×24 grid of sale counts by (weekday, hour).

    Weekday 0 = Monday, 6 = Sunday.
    Returns grid[row][col] where row is weekday (0..6), col is hour (0..23).
    """
    now = datetime.utcnow()
    start = now - timedelta(days=days)

    sales = (
        db.query(Sale.created_at)
        .filter(
            Sale.shop_id == shop_id,
            Sale.created_at >= start,
            Sale.created_at <= now,
            Sale.is_voided == False,
        )
        .all()
    )

    grid = [[0] * 24 for _ in range(7)]
    for (created_at,) in sales:
        if not created_at:
            continue
        weekday = created_at.weekday()  # Monday=0
        hour = created_at.hour
        grid[weekday][hour] += 1

    max_val = max((max(row) for row in grid), default=0)
    return {
        "window_days": days,
        "grid": grid,
        "max": max_val,
        "weekday_labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    }


# ─── NEW: GET /sessions-trend ───────────────────────────────────


@router.get("/sessions-trend")
def get_sessions_trend(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    """
    Per-day counts of sessions opened and sales made, for the last `days`.

    Fills empty days with zeros so the frontend can render a continuous
    bar chart without gaps.

    Returns:
        {
          "window_days": int,
          "items": [
             { "date": "YYYY-MM-DD", "sessions": int, "sales": int, "revenue": float }
             ...
          ],
          "totals": { "sessions": int, "sales": int, "revenue": float }
        }
    """
    now = datetime.utcnow()
    # Start at midnight of (days-1) days ago → exactly `days` calendar days
    # including today.
    start = (now - timedelta(days=days - 1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    end = start + timedelta(days=days)

    # Build a zeroed bucket for every day in range so the response is dense.
    buckets: dict[date, dict] = {}
    for i in range(days):
        d = (start + timedelta(days=i)).date()
        buckets[d] = {"date": d, "sessions": 0, "sales": 0, "revenue": 0.0}

    # ── Sessions opened per day ──
    session_rows = (
        db.query(
            func.date(SessionModel.opened_at).label("d"),
            func.count(SessionModel.id).label("cnt"),
        )
        .filter(
            SessionModel.shop_id == shop_id,
            SessionModel.opened_at >= start,
            SessionModel.opened_at < end,
        )
        .group_by(func.date(SessionModel.opened_at))
        .all()
    )
    for row in session_rows:
        key = row.d if isinstance(row.d, date) else date.fromisoformat(str(row.d))
        if key in buckets:
            buckets[key]["sessions"] = int(row.cnt or 0)

    # ── Sales (count + revenue) per day ──
    sale_rows = (
        db.query(
            func.date(Sale.created_at).label("d"),
            func.count(Sale.id).label("cnt"),
            func.coalesce(func.sum(Sale.total_amount), 0).label("rev"),
        )
        .filter(
            Sale.shop_id == shop_id,
            Sale.created_at >= start,
            Sale.created_at < end,
            Sale.is_voided == False,
        )
        .group_by(func.date(Sale.created_at))
        .all()
    )
    for row in sale_rows:
        key = row.d if isinstance(row.d, date) else date.fromisoformat(str(row.d))
        if key in buckets:
            buckets[key]["sales"] = int(row.cnt or 0)
            buckets[key]["revenue"] = float(row.rev or 0)

    items = [
        {
            "date": v["date"].isoformat(),
            "sessions": v["sessions"],
            "sales": v["sales"],
            "revenue": round(v["revenue"], 2),
        }
        for v in buckets.values()
    ]

    totals = {
        "sessions": sum(i["sessions"] for i in items),
        "sales": sum(i["sales"] for i in items),
        "revenue": round(sum(i["revenue"] for i in items), 2),
    }

    return {"window_days": days, "items": items, "totals": totals}

# ─── GET /will-run-out ──────────────────────────────────────────


@router.get("/will-run-out")
def get_will_run_out(
    days: int = Query(14, ge=1, le=60),
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    """
    Leaf products whose current stock will run out within the window,
    based on avg daily sales over the last 30 days.

    Returns: [{ id, name, unit, stock_qty, avg_daily_sales,
                days_left, suggested_reorder }]
    """
    now = datetime.utcnow()
    cutoff_30d = now - timedelta(days=30)

    sold_map = {
        row.product_id: float(row.sold or 0)
        for row in (
            db.query(
                SaleItem.product_id,
                func.sum(SaleItem.quantity).label("sold"),
            )
            .join(Sale, Sale.id == SaleItem.sale_id)
            .filter(
                Sale.shop_id == shop_id,
                Sale.created_at >= cutoff_30d,
                Sale.is_voided == False,
            )
            .group_by(SaleItem.product_id)
            .all()
        )
    }

    candidates = (
        _leaf_products_query(db, shop_id)
        .filter(Product.stock_qty >= 0)
        .all()
    )

    rows = []
    for p in candidates:
        sold = sold_map.get(p.id, 0.0)
        if sold <= 0:
            continue
        daily = sold / 30.0
        days_left = (p.stock_qty or 0) / daily
        if days_left > days:
            continue
        # suggest enough for 2 weeks, rounded up, min 1
        suggested = max(1, int(round(daily * 14)))
        rows.append({
            "id": p.id,
            "name": p.name,
            "unit": p.unit,
            "stock_qty": float(p.stock_qty or 0),
            "avg_daily_sales": round(daily, 2),
            "days_left": round(days_left, 1),
            "suggested_reorder": suggested,
        })

    rows.sort(key=lambda r: r["days_left"])
    return {"window_days": days, "products": rows[:limit]}


# ─── GET /profit-by-category ────────────────────────────────────


@router.get("/profit-by-category")
def get_profit_by_category(
    days: int = Query(30, ge=1, le=180),
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    """
    Revenue, cost, profit and margin grouped by product category
    over the window.

    Returns: [{ category, revenue, cost, profit, margin_pct, items_sold }]
    sorted by revenue desc.
    """
    now = datetime.utcnow()
    start = now - timedelta(days=days)

    rows = (
        db.query(
            Product.category,
            func.coalesce(func.sum(SaleItem.total_price), 0).label("revenue"),
            func.coalesce(func.sum(SaleItem.cost_price), 0).label("cost"),
            func.coalesce(func.sum(SaleItem.quantity), 0).label("qty"),
        )
        .join(SaleItem, SaleItem.product_id == Product.id)
        .join(Sale, Sale.id == SaleItem.sale_id)
        .filter(
            Sale.shop_id == shop_id,
            Product.shop_id == shop_id,
            Sale.created_at >= start,
            Sale.created_at <= now,
            Sale.is_voided == False,
        )
        .group_by(Product.category)
        .all()
    )

    items = []
    for r in rows:
        revenue = float(r.revenue or 0)
        cost = float(r.cost or 0)
        profit = revenue - cost
        margin = (profit / revenue * 100) if revenue > 0 else 0.0
        items.append({
            "category": r.category or "Uncategorised",
            "revenue": round(revenue, 2),
            "cost": round(cost, 2),
            "profit": round(profit, 2),
            "margin_pct": round(margin, 1),
            "items_sold": float(r.qty or 0),
        })

    items.sort(key=lambda x: x["revenue"], reverse=True)
    return {"window_days": days, "categories": items}


# ─── GET /customer-health ───────────────────────────────────────


@router.get("/customer-health")
def get_customer_health(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    """
    Customer retention signals for the window.

    - repeat_rate: % of this window's sales that came from customers
      who have ever bought more than once.
    - new_customers: customers whose first ever sale falls in the window.
    - at_risk: customers who bought >= 2 times historically but have
      not bought in the last 30 days.
    """
    now = datetime.utcnow()
    start = now - timedelta(days=days)
    cutoff_30d = now - timedelta(days=30)

    # Sales in window that have a customer attached
    window_sales = (
        db.query(Sale.id, Sale.customer_id)
        .filter(
            Sale.shop_id == shop_id,
            Sale.created_at >= start,
            Sale.created_at <= now,
            Sale.is_voided == False,
            Sale.customer_id.isnot(None),
        )
        .all()
    )

    # How many total sales per customer (ever) — for "repeat" check
    ever_counts = dict(
        db.query(Sale.customer_id, func.count(Sale.id))
        .filter(
            Sale.shop_id == shop_id,
            Sale.is_voided == False,
            Sale.customer_id.isnot(None),
        )
        .group_by(Sale.customer_id)
        .all()
    )

    total_window = len(window_sales)
    repeat_sales = sum(
        1 for s in window_sales if ever_counts.get(s.customer_id, 0) >= 2
    )
    repeat_rate = (repeat_sales / total_window * 100) if total_window else 0.0

    # New customers: first ever sale falls in the window
    first_sale_sub = (
        db.query(
            Sale.customer_id.label("cid"),
            func.min(Sale.created_at).label("first_at"),
        )
        .filter(
            Sale.shop_id == shop_id,
            Sale.is_voided == False,
            Sale.customer_id.isnot(None),
        )
        .group_by(Sale.customer_id)
        .subquery()
    )
    new_customers = (
        db.query(func.count(first_sale_sub.c.cid))
        .filter(
            first_sale_sub.c.first_at >= start,
            first_sale_sub.c.first_at <= now,
        )
        .scalar()
        or 0
    )

    # At-risk: >= 2 lifetime purchases, but none in last 30 days
    last_sale_sub = (
        db.query(
            Sale.customer_id.label("cid"),
            func.max(Sale.created_at).label("last_at"),
            func.count(Sale.id).label("cnt"),
        )
        .filter(
            Sale.shop_id == shop_id,
            Sale.is_voided == False,
            Sale.customer_id.isnot(None),
        )
        .group_by(Sale.customer_id)
        .subquery()
    )
    at_risk_rows = (
        db.query(Customer.id, Customer.name, Customer.phone)
        .join(last_sale_sub, last_sale_sub.c.cid == Customer.id)
        .filter(
            Customer.shop_id == shop_id,
            last_sale_sub.c.cnt >= 2,
            last_sale_sub.c.last_at < cutoff_30d,
        )
        .order_by(last_sale_sub.c.last_at.asc())
        .limit(5)
        .all()
    )

    return {
        "window_days": days,
        "repeat_rate": round(repeat_rate, 1),
        "repeat_sales": repeat_sales,
        "total_window_sales": total_window,
        "new_customers": int(new_customers),
        "at_risk": [
            {"id": r.id, "name": r.name, "phone": r.phone}
            for r in at_risk_rows
        ],
    }


# ─── GET /inventory-value ───────────────────────────────────────


@router.get("/inventory-value")
def get_inventory_value(
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    """
    Cash currently tied up in stock.

    - value_at_cost: Σ stock_qty × purchase_price
    - value_at_retail: Σ stock_qty × selling_price
    - turnover: COGS last 90d / value_at_cost  (annualised × 4)
    """
    now = datetime.utcnow()

    row = (
        db.query(
            func.coalesce(
                func.sum(Product.stock_qty * Product.purchase_price), 0
            ).label("cost"),
            func.coalesce(
                func.sum(Product.stock_qty * Product.selling_price), 0
            ).label("retail"),
            func.count(Product.id).label("count"),
        )
        .filter(
            Product.shop_id == shop_id,
            Product.is_deleted == False,
            Product.archived == False,
            Product.stock_qty > 0,
        )
        .one()
    )

    value_at_cost = float(row.cost or 0)
    value_at_retail = float(row.retail or 0)
    sku_count = int(row.count or 0)

    # COGS last 90d for turnover
    cutoff_90d = now - timedelta(days=90)
    cogs_90d = (
        db.query(func.coalesce(func.sum(SaleItem.cost_price), 0))
        .join(Sale, Sale.id == SaleItem.sale_id)
        .filter(
            Sale.shop_id == shop_id,
            Sale.created_at >= cutoff_90d,
            Sale.is_voided == False,
        )
        .scalar()
        or 0
    )
    cogs_90d = float(cogs_90d)

    if value_at_cost > 0:
        # quarterly turnover → annualise
        turnover_annual = (cogs_90d / value_at_cost) * 4
    else:
        turnover_annual = 0.0

    return {
        "value_at_cost": round(value_at_cost, 2),
        "value_at_retail": round(value_at_retail, 2),
        "potential_margin": round(value_at_retail - value_at_cost, 2),
        "sku_count": sku_count,
        "cogs_90d": round(cogs_90d, 2),
        "turnover_annual": round(turnover_annual, 2),
    }


# ─── GET /expense-breakdown ─────────────────────────────────────


@router.get("/expense-breakdown")
def get_expense_breakdown(
    days: int = Query(30, ge=1, le=180),
    limit: int = Query(6, ge=1, le=20),
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    """
    Top expense categories in the window.

    Returns: [{ category, total, count, share_pct }] sorted by total desc.
    """
    now = datetime.utcnow()
    start = now - timedelta(days=days)

    rows = (
        db.query(
            Expense.category,
            func.coalesce(func.sum(Expense.amount), 0).label("total"),
            func.count(Expense.id).label("cnt"),
        )
        .filter(
            Expense.shop_id == shop_id,
            Expense.created_at >= start,
            Expense.created_at <= now,
        )
        .group_by(Expense.category)
        .order_by(func.sum(Expense.amount).desc())
        .limit(limit)
        .all()
    )

    grand_total = sum(float(r.total or 0) for r in rows)

    return {
        "window_days": days,
        "total": round(grand_total, 2),
        "categories": [
            {
                "category": r.category or "Uncategorised",
                "total": round(float(r.total or 0), 2),
                "count": int(r.cnt or 0),
                "share_pct": round(
                    (float(r.total or 0) / grand_total * 100) if grand_total else 0, 1
                ),
            }
            for r in rows
        ],
    }


# ─── GET /good-news ─────────────────────────────────────────────


@router.get("/good-news")
def get_good_news(
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    """
    A short rotating list of positive facts. Up to 3 items.
    If nothing positive exists, returns an empty list.
    """
    now = datetime.utcnow()
    week_start = now - timedelta(days=7)
    prev_start = now - timedelta(days=14)
    month_start = now - timedelta(days=30)

    items: list[dict] = []

    # 1. Best weekday in the last 4 weeks vs the previous 4 weeks
    def _weekday_revenue(start, end):
        rows = (
            db.query(
                func.strftime("%w", Sale.created_at).label("wd"),
                func.coalesce(func.sum(Sale.total_amount), 0).label("rev"),
            )
            .filter(
                Sale.shop_id == shop_id,
                Sale.created_at >= start,
                Sale.created_at < end,
                Sale.is_voided == False,
            )
            .group_by(func.strftime("%w", Sale.created_at))
            .all()
        )
        return {str(r.wd): float(r.rev or 0) for r in rows}

    # NOTE: strftime is SQLite-specific. If you migrate to Postgres,
    # replace with func.extract("dow", Sale.created_at).
    # Keeping it simple here to match your SQLite dev DB.

    # 2. Revenue up vs last week
    cur = _revenue_and_profit_for_window(db, shop_id, week_start, now)
    prev = _revenue_and_profit_for_window(db, shop_id, prev_start, week_start)
    if prev["revenue"] > 0 and cur["revenue"] > prev["revenue"]:
        pct = (cur["revenue"] - prev["revenue"]) / prev["revenue"] * 100
        if pct >= 5:
            items.append({
                "icon": "trending-up",
                "text": f"Revenue up {pct:.0f}% vs last week",
            })

    # 3. Profit margin improved vs last month
    cur_m = _revenue_and_profit_for_window(db, shop_id, month_start, now)
    if cur_m["revenue"] > 0:
        margin_now = (cur_m["profit"] / cur_m["revenue"]) * 100
        prev_m = _revenue_and_profit_for_window(
            db, shop_id, month_start - timedelta(days=30), month_start
        )
        if prev_m["revenue"] > 0:
            margin_prev = (prev_m["profit"] / prev_m["revenue"]) * 100
            if margin_now - margin_prev >= 3:
                items.append({
                    "icon": "trending-up",
                    "text": f"Profit margin up {margin_now - margin_prev:.1f} pts this month",
                })

    # 4. New repeat customers this week
    first_sale_sub = (
        db.query(
            Sale.customer_id.label("cid"),
            func.min(Sale.created_at).label("first_at"),
            func.count(Sale.id).label("cnt"),
        )
        .filter(
            Sale.shop_id == shop_id,
            Sale.is_voided == False,
            Sale.customer_id.isnot(None),
            Sale.created_at >= week_start,
            Sale.created_at <= now,
        )
        .group_by(Sale.customer_id)
        .subquery()
    )
    repeat_new = (
        db.query(func.count(first_sale_sub.c.cid))
        .filter(first_sale_sub.c.cnt >= 2)
        .scalar()
        or 0
    )
    if repeat_new > 0:
        items.append({
            "icon": "users",
            "text": f"{repeat_new} new customer{'s' if repeat_new != 1 else ''} already came back this week",
        })

    # 5. No overdue debtors
    cutoff_14d = now - timedelta(days=14)
    overdue_count = 0
    for c in (
        db.query(Customer)
        .filter(Customer.shop_id == shop_id, Customer.total_credit > 0)
        .all()
    ):
        last_payment = (
            db.query(func.max(Payment.created_at))
            .filter(Payment.customer_id == c.id, Payment.shop_id == shop_id)
            .scalar()
        )
        if last_payment is None or last_payment < cutoff_14d:
            overdue_count += 1
    if overdue_count == 0 and (
        db.query(Customer)
        .filter(Customer.shop_id == shop_id, Customer.total_credit > 0)
        .count()
    ) > 0:
        items.append({
            "icon": "check-circle",
            "text": "No overdue debtors — all credit is current",
        })

    return {"items": items[:3]}