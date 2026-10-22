from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_shop_id
from app.db.models.expense import Expense
from app.db.models.product import Product  # 🔧 added for name lookup
from app.db.models.sale import Sale, SaleItem
from app.db.models.session import Session as SessionModel
from app.db.session import get_db

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/")
def get_dashboard(
    session_id: str = Query(None),
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    # If no session_id provided, try to use the currently active session (scoped to shop)
    if not session_id:
        active_session = (
            db.query(SessionModel)
            .filter(
                SessionModel.is_active == True,
                SessionModel.shop_id == shop_id,  # 🔧 FIX #2: shop filter
            )
            .first()
        )
        if active_session:
            session_id = active_session.id

    # Base query for SaleItem – optionally filter by session
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
        total_cost += item.cost_price or 0  # 🔧 FIX #3: cost_price is already total
        total_quantity += item.quantity
        product_sales[item.product_id] = product_sales.get(item.product_id, 0) + item.quantity

    # Total expenses – also filter by session
    expenses_query = db.query(func.sum(Expense.amount)).filter(  # 🔧 FIX #1: valid query
        Expense.shop_id == shop_id
    )
    if session_id:
        expenses_query = expenses_query.filter(Expense.session_id == session_id)
    total_expenses = expenses_query.scalar() or 0.0

    # Profit = revenue - cost - expenses
    profit = total_revenue - total_cost - total_expenses

    # Top products (list of [product_id, quantity] tuples)
    top_products = sorted(product_sales.items(), key=lambda x: x[1], reverse=True)[:5]

    # Best / worst product — resolve IDs to names                # 🔧 FIX #4
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
        "avg_sale_value": avg_item_price,  # kept key for frontend compatibility
        "profit_margin": profit_margin,
        "total_expenses": total_expenses,
    }
