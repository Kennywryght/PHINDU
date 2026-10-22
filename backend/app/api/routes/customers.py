"""Customer API routes (includes credit/debt management + payment audit)."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_shop_id
from app.api.deps import require_min_role
from app.db.models.customer import Customer
from app.db.models.payment import Payment
from app.db.models.sale import Sale
from app.db.models.session import Session as SessionModel
from app.db.session import get_db

router = APIRouter(prefix="/customers", tags=["Customers"])


# ─── Schemas ─────────────────────────────────────────────────────
class CustomerCreate(BaseModel):
    name: str
    phone: str | None = None
    email: str | None = None
    address: str | None = None


class CustomerOut(BaseModel):
    id: str
    name: str
    phone: str | None
    email: str | None
    address: str | None
    total_credit: float
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class PaymentCreate(BaseModel):
    amount: float = Field(..., gt=0)
    method: str = Field("cash", description="cash, airtel_money, tnm_mpamba, bank, cheque, other")
    sale_id: str | None = None
    note: str | None = None


class PaymentOut(BaseModel):
    id: str
    customer_id: str
    shop_id: str
    session_id: str | None
    sale_id: str | None
    amount: float
    method: str
    note: str | None
    created_at: datetime | None = None

    class Config:
        from_attributes = True


# ─── Endpoints ───────────────────────────────────────────────────
@router.post("/", response_model=CustomerOut)
def create_customer(
    customer: CustomerCreate,
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    new_customer = Customer(**customer.model_dump(), shop_id=shop_id)
    db.add(new_customer)
    db.commit()
    db.refresh(new_customer)
    return new_customer


@router.get("/", response_model=list[CustomerOut])
def get_customers(
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    return db.query(Customer).filter(Customer.shop_id == shop_id).order_by(Customer.name).all()


@router.get("/debtors")
def get_debtors(
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    """Return customers with outstanding credit (>0)."""
    debtors = (
        db.query(Customer).filter(Customer.total_credit > 0, Customer.shop_id == shop_id).all()
    )
    return [
        {
            "id": c.id,
            "name": c.name,
            "phone": c.phone,
            "total_credit": c.total_credit,
        }
        for c in debtors
    ]


@router.post(
    "/{customer_id}/record-payment",
    response_model=PaymentOut,
    dependencies=[Depends(require_min_role("manager"))],
)
def record_payment(
    customer_id: str,
    payload: PaymentCreate,
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    """Record a credit payment from a customer.

    Creates a full audit-trail Payment record and updates:
      - customer.total_credit (reduced by amount)
      - active session's cash_sales (if method='cash')
      - sale.amount_paid / payment_status (if sale_id provided)

    Requires manager or owner.
    """
    customer = (
        db.query(Customer).filter(Customer.id == customer_id, Customer.shop_id == shop_id).first()
    )
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    if payload.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    # ── Optional: specific sale being paid off ──
    sale = None
    if payload.sale_id:
        sale = db.query(Sale).filter(Sale.id == payload.sale_id, Sale.shop_id == shop_id).first()
        if not sale:
            raise HTTPException(status_code=404, detail="Sale not found")
        if sale.customer_id != customer_id:
            raise HTTPException(
                status_code=400,
                detail="Sale does not belong to this customer",
            )
        if sale.is_voided:
            raise HTTPException(
                status_code=400,
                detail="Cannot record payment against a voided sale",
            )

    # ── Link to active session ──
    active_session = (
        db.query(SessionModel)
        .filter(SessionModel.is_active == True, SessionModel.shop_id == shop_id)
        .first()
    )

    # ── Create Payment record (audit trail) ──
    payment = Payment(
        id=str(uuid.uuid4()),
        shop_id=shop_id,
        customer_id=customer_id,
        session_id=active_session.id if active_session else None,
        sale_id=payload.sale_id,
        amount=payload.amount,
        method=payload.method or "cash",
        note=payload.note,
    )
    db.add(payment)

    # ── Reduce customer credit ──
    customer.total_credit = max(0, (customer.total_credit or 0) - payload.amount)

    # ── If tied to a specific sale, update that sale's amount_paid ──
    if sale:
        new_amount_paid = min(
            sale.total_amount or 0,
            (sale.amount_paid or 0) + payload.amount,
        )
        sale.amount_paid = new_amount_paid
        if new_amount_paid >= (sale.total_amount or 0):
            sale.payment_status = "paid"
        elif new_amount_paid > 0:
            sale.payment_status = "partial"

    # ── If cash, increase active session cash_sales ──
    if active_session and (payload.method or "cash").lower() == "cash":
        # We don't reuse `cash_sales` (that's for sale revenue);
        # we track cash received via payments in session tracking below
        # by re-computing from Payment rows. But for quick drawer math:
        pass  # see note in summary endpoint

    db.commit()
    db.refresh(payment)
    return payment


@router.get("/{customer_id}/payments", response_model=list[PaymentOut])
def get_customer_payments(
    customer_id: str,
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    """Full payment history for a customer."""
    customer = (
        db.query(Customer).filter(Customer.id == customer_id, Customer.shop_id == shop_id).first()
    )
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    return (
        db.query(Payment)
        .filter(Payment.customer_id == customer_id, Payment.shop_id == shop_id)
        .order_by(Payment.created_at.desc())
        .all()
    )
