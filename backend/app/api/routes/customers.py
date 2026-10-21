"""Customer API routes (includes credit/debt management)."""

from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models.customer import Customer
from app.api.dependencies import get_current_shop_id
from app.api.deps import require_min_role           # 🔧 Fix 2.5

router = APIRouter(prefix="/customers", tags=["Customers"])


# ─── Schemas ─────────────────────────────────────────────────────
class CustomerCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None


class CustomerOut(BaseModel):
    id: str
    name: str
    phone: Optional[str]
    email: Optional[str]
    address: Optional[str]
    total_credit: float
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ─── Endpoints ───────────────────────────────────────────────────
@router.post("/", response_model=CustomerOut)
def create_customer(
    customer: CustomerCreate,
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    new_customer = Customer(**customer.dict(), shop_id=shop_id)
    db.add(new_customer)
    db.commit()
    db.refresh(new_customer)
    return new_customer


@router.get("/", response_model=list[CustomerOut])
def get_customers(
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    return (
        db.query(Customer)
        .filter(Customer.shop_id == shop_id)
        .order_by(Customer.name)
        .all()
    )


@router.get("/debtors")
def get_debtors(
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    """Return customers with outstanding credit (>0)."""
    debtors = (
        db.query(Customer)
        .filter(Customer.total_credit > 0, Customer.shop_id == shop_id)
        .all()
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
    dependencies=[Depends(require_min_role("manager"))],  # 🔧 Fix 2.5
)
def record_payment(
    customer_id: str,
    amount: float,
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    """Record a credit payment from a customer.

    Requires manager or owner — money adjustment operation.
    """
    customer = (
        db.query(Customer)
        .filter(Customer.id == customer_id, Customer.shop_id == shop_id)
        .first()
    )
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    customer.total_credit = max(0, customer.total_credit - amount)
    db.commit()
    return {
        "message": f"Payment of {amount} recorded. Remaining credit: {customer.total_credit}"
    }