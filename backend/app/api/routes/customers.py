"""Customer API routes (credit/debt + payment audit + risk scoring)."""

import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
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


# ─── Credit Risk Scoring (pure logic) ────────────────────────────
def _compute_credit_risk(db: Session, customer: Customer, shop_id: str) -> dict:
    """
    Compute a 0-100 credit risk score for a customer.

    Higher = safer to extend credit.

    A brand-new customer with no history and no outstanding balance
    scores a perfect 100. Deductions only apply when there is actual
    credit exposure or negative history.
    """
    now = datetime.utcnow()
    score = 100
    warnings = []
    positives = []

    payments = (
        db.query(Payment)
        .filter(Payment.customer_id == customer.id, Payment.shop_id == shop_id)
        .all()
    )

    sales = (
        db.query(Sale)
        .filter(
            Sale.customer_id == customer.id,
            Sale.shop_id == shop_id,
            Sale.is_voided == False,
        )
        .all()
    )

    payment_count = len(payments)
    sale_count = len(sales)
    total_paid = sum(p.amount or 0 for p in payments)
    total_sold = sum(s.total_amount or 0 for s in sales)
    credit_sales_amount = sum(
        s.total_amount or 0 for s in sales
        if s.payment_status in ("unpaid", "partial")
    )
    current_balance = customer.total_credit or 0

    account_age_days = None
    if customer.created_at:
        account_age_days = (now - customer.created_at).days

    avg_purchase = (total_sold / sale_count) if sale_count > 0 else 0

    avg_days_to_pay = None
    if payment_count > 0 and credit_sales_amount > 0:
        credit_sales = [
            s for s in sales
            if s.payment_status in ("unpaid", "partial") or s.amount_paid
        ]
        if credit_sales:
            first_credit_sale = min(s.created_at for s in credit_sales)
            last_payment = max(p.created_at for p in payments)
            if first_credit_sale and last_payment and last_payment >= first_credit_sale:
                avg_days_to_pay = (last_payment - first_credit_sale).days

    credit_ratio = (credit_sales_amount / total_sold) if total_sold > 0 else 0

    if current_balance > 0 and payment_count == 0:
        score -= 40
        warnings.append("Never made a payment on record")

    if avg_days_to_pay is not None:
        if avg_days_to_pay > 45:
            score -= 25
            warnings.append(f"Very slow payer ({avg_days_to_pay} days average)")
        elif avg_days_to_pay > 30:
            score -= 15
            warnings.append(f"Slow payer ({avg_days_to_pay} days average)")
        elif avg_days_to_pay > 14:
            score -= 8
            warnings.append(f"Moderate payer ({avg_days_to_pay} days average)")
        elif avg_days_to_pay <= 10 and payment_count >= 2:
            score += 5
            positives.append(f"Fast payer ({avg_days_to_pay} days average)")

    if avg_purchase > 0 and current_balance > 0:
        ratio = current_balance / avg_purchase
        if ratio > 4:
            score -= 25
            warnings.append(f"Balance is {ratio:.1f}× typical purchase")
        elif ratio > 2:
            score -= 15
            warnings.append(f"Balance is {ratio:.1f}× typical purchase")
        elif ratio > 1:
            score -= 8

    if credit_ratio >= 0.5:
        score -= 20
        warnings.append(f"{int(credit_ratio * 100)}% of sales were on credit")
    elif credit_ratio >= 0.3:
        score -= 10

    if (
        account_age_days is not None
        and account_age_days < 30
        and current_balance > 0
    ):
        score -= 10
        warnings.append(f"New account ({account_age_days} days old)")

    if payment_count >= 5:
        score += 5
        positives.append(f"{payment_count} successful payments")
    elif payment_count >= 1 and payment_count < 5:
        positives.append(f"{payment_count} payment(s) on record")

    score = max(0, min(100, score))

    has_history = sale_count > 0 or payment_count > 0

    if not has_history:
        level = "new"
        label = "New Customer"
        recommendation = "No purchase history yet — start with a small credit limit"
    elif score >= 70:
        level = "low"
        label = "Low Risk"
        recommendation = "Safe to extend credit"
    elif score >= 40:
        level = "medium"
        label = "Medium Risk"
        recommendation = "Extend credit with caution — monitor closely"
    else:
        level = "high"
        label = "High Risk"
        recommendation = "Consider declining new credit or requiring prepayment"

    return {
        "score": score,
        "level": level,
        "label": label,
        "recommendation": recommendation,
        "factors": {
            "payment_count": payment_count,
            "sale_count": sale_count,
            "total_paid": round(total_paid, 2),
            "total_sold": round(total_sold, 2),
            "credit_sales_amount": round(credit_sales_amount, 2),
            "credit_ratio": round(credit_ratio, 2),
            "current_balance": round(current_balance, 2),
            "avg_purchase": round(avg_purchase, 2),
            "avg_days_to_pay": avg_days_to_pay,
            "account_age_days": account_age_days,
        },
        "warnings": warnings,
        "positives": positives,
    }


# ─── Overdue bucket helper ───────────────────────────────────────
def _overdue_bucket(days_since_last_payment: int | None, never_paid: bool) -> str:
    """
    Bucket a debtor by how overdue their last payment is.

    - "never"    → never paid anything
    - "critical" → 30+ days or never
    - "overdue"  → 14–29 days
    - "warning"  → 7–13 days
    - "ok"       → < 7 days
    """
    if never_paid:
        return "never"
    if days_since_last_payment is None:
        return "never"
    if days_since_last_payment >= 30:
        return "critical"
    if days_since_last_payment >= 14:
        return "overdue"
    if days_since_last_payment >= 7:
        return "warning"
    return "ok"


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
    include_risk: bool = Query(False, description="Include credit risk scores"),
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    """
    Return customers with outstanding credit (>0).

    Each debtor includes:
      - last_payment_date
      - days_since_last_payment
      - never_paid
      - overdue_bucket  (ok / warning / overdue / critical / never)
    """
    debtors = (
        db.query(Customer)
        .filter(Customer.total_credit > 0, Customer.shop_id == shop_id)
        .all()
    )

    # Batch-fetch last payment per debtor (one query)
    last_payments: dict[str, datetime] = {}
    if debtors:
        debtor_ids = [c.id for c in debtors]
        rows = (
            db.query(Payment.customer_id, func.max(Payment.created_at).label("last_paid"))
            .filter(
                Payment.customer_id.in_(debtor_ids),
                Payment.shop_id == shop_id,
            )
            .group_by(Payment.customer_id)
            .all()
        )
        for row in rows:
            if row.last_paid:
                last_payments[row.customer_id] = row.last_paid

    now = datetime.utcnow()
    result = []
    for c in debtors:
        last_payment = last_payments.get(c.id)
        never_paid = last_payment is None
        days_since = (now - last_payment).days if last_payment else None

        item = {
            "id": c.id,
            "name": c.name,
            "phone": c.phone,
            "total_credit": float(c.total_credit or 0),
            "last_payment_date": last_payment.isoformat() if last_payment else None,
            "days_since_last_payment": days_since,
            "never_paid": never_paid,
            "overdue_bucket": _overdue_bucket(days_since, never_paid),
        }
        if include_risk:
            item["risk"] = _compute_credit_risk(db, c, shop_id)
        result.append(item)

    if include_risk:
        level_priority = {"high": 0, "medium": 1, "new": 2, "low": 3}
        result.sort(
            key=lambda x: (
                level_priority.get(x["risk"]["level"], 4),
                -x["total_credit"],
            )
        )
    else:
        result.sort(key=lambda x: x["total_credit"], reverse=True)

    return result


@router.get("/{customer_id}/credit-risk")
def get_customer_credit_risk(
    customer_id: str,
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    """Compute and return the credit risk score for a specific customer."""
    customer = (
        db.query(Customer).filter(Customer.id == customer_id, Customer.shop_id == shop_id).first()
    )
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    risk = _compute_credit_risk(db, customer, shop_id)
    return {
        "customer_id": customer.id,
        "name": customer.name,
        **risk,
    }


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
    """Record a credit payment from a customer."""
    customer = (
        db.query(Customer).filter(Customer.id == customer_id, Customer.shop_id == shop_id).first()
    )
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    if payload.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

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

    active_session = (
        db.query(SessionModel)
        .filter(SessionModel.is_active == True, SessionModel.shop_id == shop_id)
        .first()
    )

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

    customer.total_credit = max(0, (customer.total_credit or 0) - payload.amount)

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