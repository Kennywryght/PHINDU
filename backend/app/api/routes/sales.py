"""Sales API routes."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_shop_id
from app.api.deps import require_min_role
from app.db.models.customer import Customer
from app.db.models.product import Product
from app.db.models.sale import Sale, SaleItem
from app.db.models.session import Session as SessionModel
from app.db.models.stock import StockBatch
from app.db.session import get_db
from app.schemas.sale import BulkSaleCreate, SaleCreate, SaleResponse
from app.utils.conversion import to_kg

router = APIRouter(prefix="/sales", tags=["Sales"])

# Placeholder values Swagger/frontend might send for optional fields
_PLACEHOLDER_VALUES = {"", "string", "null", "undefined", "none", "None"}


def _clean_optional_str(value: str | None) -> str | None:
    """Normalize placeholder strings to None."""
    if value is None:
        return None
    if isinstance(value, str) and value.strip() in _PLACEHOLDER_VALUES:
        return None
    return value


def _normalize_payment_status(value: str | None) -> str:
    """Ensure payment_status is one of the allowed values."""
    if value in {"paid", "unpaid", "partial"}:
        return value
    return "paid"


def _validate_payment_amounts(
    payment_status: str,
    total_amount: float,
    amount_paid: float,
) -> float:
    """
    Enforce consistency between payment_status and amount_paid.

    Rules:
    - "paid"    → amount_paid must equal total_amount (auto-fixed if 0/None)
    - "unpaid"  → amount_paid must be 0
    - "partial" → 0 < amount_paid < total_amount

    Returns the (possibly corrected) amount_paid value.
    """
    if payment_status == "paid":
        # Force full payment
        return total_amount
    if payment_status == "unpaid":
        if amount_paid and amount_paid > 0:
            raise HTTPException(
                status_code=400,
                detail="payment_status='unpaid' requires amount_paid to be 0 or omitted",
            )
        return 0.0
    if payment_status == "partial":
        if amount_paid is None or amount_paid <= 0:
            raise HTTPException(
                status_code=400,
                detail="payment_status='partial' requires amount_paid > 0",
            )
        if amount_paid >= total_amount:
            raise HTTPException(
                status_code=400,
                detail="payment_status='partial' requires amount_paid < total_amount; use 'paid' instead",
            )
        return amount_paid
    # Should never reach here (normalized before call), but defensive:
    return 0.0


def _update_session_cash(
    session: SessionModel | None,
    payment_status: str,
    total_amount: float,
) -> None:
    """Update session cash/credit totals based on this sale."""
    if session is None:
        return
    if payment_status == "paid":
        session.cash_sales = (session.cash_sales or 0) + total_amount
    else:
        session.credit_sales = (session.credit_sales or 0) + total_amount


@router.post("/", response_model=SaleResponse)
def create_sale(
    sale: SaleCreate,
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    """Create a new sale with items, update stock, and calculate totals.

    Payment rules enforced:
    - "paid"    → amount_paid auto-set to total
    - "unpaid"  → amount_paid = 0, credit increased for customer
    - "partial" → 0 < amount_paid < total, credit increased by remainder
    """
    if not sale.items:
        raise HTTPException(status_code=400, detail="Sale must have at least one item")

    customer_id = _clean_optional_str(sale.customer_id)
    customer = None
    if customer_id:
        customer = (
            db.query(Customer)
            .filter(Customer.id == customer_id, Customer.shop_id == shop_id)
            .first()
        )
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")

    payment_status = _normalize_payment_status(sale.payment_status)

    if payment_status in ("unpaid", "partial") and not customer:
        raise HTTPException(
            status_code=400,
            detail=f"payment_status='{payment_status}' requires a customer_id",
        )

    new_sale = Sale(
        id=str(uuid.uuid4()),
        total_amount=0,
        shop_id=shop_id,
        customer_id=customer_id,
        payment_status=payment_status,
        amount_paid=0.0,  # set correctly below after we know total
    )

    active_session = (
        db.query(SessionModel)
        .filter(SessionModel.is_active == True, SessionModel.shop_id == shop_id)
        .first()
    )
    if active_session:
        new_sale.session_id = active_session.id

    db.add(new_sale)

    total_amount = 0.0

    try:
        for item in sale.items:
            product = (
                db.query(Product)
                .filter(Product.id == item.product_id, Product.shop_id == shop_id)
                .first()
            )
            if not product:
                raise HTTPException(
                    status_code=404,
                    detail=f"Product not found: {item.product_id}",
                )

            if product.type == "bulk":
                if not item.unit:
                    raise HTTPException(
                        status_code=400,
                        detail="Unit required for bulk products",
                    )
                qty_in_kg = to_kg(item.quantity, item.unit)
                if product.stock_qty < qty_in_kg:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Not enough stock for {product.name}",
                    )
                total_price = qty_in_kg * product.selling_price
                cost_price = (product.purchase_price or 0) * qty_in_kg
                product.stock_qty -= qty_in_kg
            else:
                if product.stock_qty < item.quantity:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Not enough stock for {product.name}",
                    )
                total_price = item.quantity * product.selling_price
                cost_price = (product.purchase_price or 0) * item.quantity
                product.stock_qty -= item.quantity

                if product.stock_qty <= 0:
                    batch = (
                        db.query(StockBatch)
                        .filter(
                            StockBatch.product_id == product.id,
                            StockBatch.shop_id == shop_id,
                        )
                        .order_by(StockBatch.date_added.desc())
                        .first()
                    )
                    if batch and not batch.date_finished:
                        batch.date_finished = datetime.utcnow()

            total_amount += total_price

            sale_item = SaleItem(
                id=str(uuid.uuid4()),
                shop_id=shop_id,
                sale_id=new_sale.id,
                product_id=product.id,
                quantity=item.quantity,
                unit_price=product.selling_price,
                total_price=total_price,
                cost_price=cost_price,
            )
            db.add(sale_item)

        new_sale.total_amount = total_amount

        # Enforce payment_status ↔ amount_paid consistency
        new_sale.amount_paid = _validate_payment_amounts(
            payment_status, total_amount, sale.amount_paid or 0.0
        )

        # Update customer credit for unpaid/partial sales
        if customer and payment_status != "paid":
            owed = total_amount - new_sale.amount_paid
            if owed > 0:
                customer.total_credit = (customer.total_credit or 0) + owed

        # Update session cash/credit tracking
        _update_session_cash(active_session, payment_status, total_amount)

        db.commit()
        db.refresh(new_sale)
        return new_sale

    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise


@router.post("/bulk")
def bulk_sales(
    data: BulkSaleCreate,
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    """Quick bulk sales — one Sale record with multiple SaleItems."""
    if not data.items:
        raise HTTPException(status_code=400, detail="Sale must have at least one item")

    customer_id = _clean_optional_str(data.customer_id)
    customer = None
    if customer_id:
        customer = (
            db.query(Customer)
            .filter(Customer.id == customer_id, Customer.shop_id == shop_id)
            .first()
        )
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")

    payment_status = _normalize_payment_status(data.payment_status)

    if payment_status in ("unpaid", "partial") and not customer:
        raise HTTPException(
            status_code=400,
            detail=f"payment_status='{payment_status}' requires a customer_id",
        )

    active_session = (
        db.query(SessionModel)
        .filter(SessionModel.is_active == True, SessionModel.shop_id == shop_id)
        .first()
    )

    new_sale = Sale(
        id=str(uuid.uuid4()),
        total_amount=0,
        shop_id=shop_id,
        customer_id=customer_id,
        payment_status=payment_status,
        amount_paid=0.0,
        session_id=active_session.id if active_session else None,
    )
    db.add(new_sale)

    total_amount = 0.0

    try:
        for item in data.items:
            product = (
                db.query(Product).filter(Product.id == item.id, Product.shop_id == shop_id).first()
            )
            if not product:
                raise HTTPException(
                    status_code=404,
                    detail=f"Product not found: {item.id}",
                )
            if product.stock_qty < item.qty:
                raise HTTPException(
                    status_code=400,
                    detail=f"Not enough stock for {product.name}",
                )

            total_price = product.selling_price * item.qty
            cost_price = (product.purchase_price or 0) * item.qty
            product.stock_qty -= item.qty

            sale_item = SaleItem(
                id=str(uuid.uuid4()),
                shop_id=shop_id,
                sale_id=new_sale.id,
                product_id=product.id,
                quantity=item.qty,
                unit_price=product.selling_price,
                total_price=total_price,
                cost_price=cost_price,
            )
            db.add(sale_item)
            total_amount += total_price

        new_sale.total_amount = total_amount
        new_sale.amount_paid = _validate_payment_amounts(
            payment_status, total_amount, data.amount_paid or 0.0
        )

        if customer and payment_status != "paid":
            owed = total_amount - new_sale.amount_paid
            if owed > 0:
                customer.total_credit = (customer.total_credit or 0) + owed

        _update_session_cash(active_session, payment_status, total_amount)

        db.commit()
        db.refresh(new_sale)

        return {
            "message": "Bulk sale recorded",
            "sale_id": new_sale.id,
            "total_amount": total_amount,
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise


@router.get("/")
def get_sales(
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    sales = db.query(Sale).filter(Sale.shop_id == shop_id).order_by(Sale.created_at.desc()).all()

    sale_ids = [s.id for s in sales]
    items_by_sale: dict[str, list[str]] = {}
    if sale_ids:
        rows = (
            db.query(SaleItem.sale_id, Product.name)
            .join(Product, Product.id == SaleItem.product_id)
            .filter(SaleItem.sale_id.in_(sale_ids))
            .all()
        )
        for sale_id, name in rows:
            items_by_sale.setdefault(sale_id, []).append(name)

    result = []
    for sale in sales:
        result.append(
            {
                "id": sale.id,
                "total_amount": sale.total_amount,
                "amount_paid": sale.amount_paid,
                "created_at": sale.created_at,
                "payment_status": sale.payment_status,
                "is_voided": sale.is_voided,
                "products": items_by_sale.get(sale.id, []),
            }
        )
    return result


@router.post(
    "/{sale_id}/void",
    dependencies=[Depends(require_min_role("manager"))],
)
def void_sale(
    sale_id: str,
    reason: str = Query(None),
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    """Void a sale and restore stock.

    Requires manager or owner (cashiers cannot void — fraud prevention).
    """
    sale = db.query(Sale).filter(Sale.id == sale_id, Sale.shop_id == shop_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    if sale.is_voided:
        raise HTTPException(status_code=400, detail="Sale already voided")

    items = db.query(SaleItem).filter(SaleItem.sale_id == sale_id).all()

    for item in items:
        product = (
            db.query(Product)
            .filter(Product.id == item.product_id, Product.shop_id == shop_id)
            .first()
        )
        if product:
            product.stock_qty += item.quantity

    # Reverse customer credit if this was a credit sale
    if sale.customer_id and sale.payment_status != "paid":
        customer = (
            db.query(Customer)
            .filter(Customer.id == sale.customer_id, Customer.shop_id == shop_id)
            .first()
        )
        if customer:
            owed = (sale.total_amount or 0) - (sale.amount_paid or 0)
            if owed > 0:
                customer.total_credit = max(0, (customer.total_credit or 0) - owed)

    # Reverse session cash/credit tracking
    if sale.session_id:
        session = db.query(SessionModel).filter(SessionModel.id == sale.session_id).first()
        if session:
            if sale.payment_status == "paid":
                session.cash_sales = max(0, (session.cash_sales or 0) - (sale.total_amount or 0))
            else:
                session.credit_sales = max(
                    0, (session.credit_sales or 0) - (sale.total_amount or 0)
                )

    sale.is_voided = True
    sale.void_reason = reason
    db.commit()
    return {"message": "Sale voided successfully"}
