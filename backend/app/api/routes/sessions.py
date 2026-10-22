"""Sessions (daily shift) API routes."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_shop_id
from app.api.deps import require_min_role
from app.db.models.expense import Expense
from app.db.models.payment import Payment
from app.db.models.sale import Sale
from app.db.models.session import Session as SessionModel
from app.db.session import get_db

router = APIRouter(prefix="/sessions", tags=["Sessions"])


def _session_to_dict(s: SessionModel) -> dict:
    """Serialize a Session ORM object to a plain dict.

    Avoids the expire-on-commit + detached-instance problem that causes
    FastAPI to silently drop fields when returning raw ORM objects.
    """
    return {
        "id": s.id,
        "shop_id": s.shop_id,
        "opened_at": s.opened_at,
        "closed_at": s.closed_at,
        "opening_balance": s.opening_balance,
        "closing_balance": s.closing_balance,
        "total_sales": s.total_sales,
        "cash_sales": s.cash_sales,
        "credit_sales": s.credit_sales,
        "total_expenses": s.total_expenses,
        "cash_removed": s.cash_removed,
        "cash_added": s.cash_added,
        "is_active": s.is_active,
        "notes": s.notes,
    }


@router.post("/open")
def open_session(
    opening_balance: float = Query(0.0),
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    """Open a new session (daily shift)."""
    active = (
        db.query(SessionModel)
        .filter(SessionModel.is_active == True, SessionModel.shop_id == shop_id)
        .first()
    )
    if active:
        raise HTTPException(status_code=400, detail="A session is already open")

    new_session = SessionModel(
        id=str(uuid.uuid4()),
        opening_balance=opening_balance,
        is_active=True,
        shop_id=shop_id,
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return _session_to_dict(new_session)


@router.post(
    "/close",
    dependencies=[Depends(require_min_role("manager"))],
)
def close_session(
    closing_balance: float,
    notes: str = None,
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    """Close the active session. Computes totals from live data."""
    active = (
        db.query(SessionModel)
        .filter(SessionModel.is_active == True, SessionModel.shop_id == shop_id)
        .first()
    )
    if not active:
        raise HTTPException(status_code=404, detail="No active session")

    sales_total = (
        db.query(Sale)
        .filter(
            Sale.session_id == active.id,
            Sale.shop_id == shop_id,
            Sale.is_voided == False,
        )
        .with_entities(func.sum(Sale.total_amount))
        .scalar()
        or 0
    )
    cash_sales_total = (
        db.query(Sale)
        .filter(
            Sale.session_id == active.id,
            Sale.shop_id == shop_id,
            Sale.is_voided == False,
            Sale.payment_status == "paid",
        )
        .with_entities(func.sum(Sale.total_amount))
        .scalar()
        or 0
    )
    expenses_total = (
        db.query(Expense)
        .filter(Expense.session_id == active.id, Expense.shop_id == shop_id)
        .with_entities(func.sum(Expense.amount))
        .scalar()
        or 0
    )

    active.closed_at = datetime.utcnow()
    active.closing_balance = closing_balance
    active.total_sales = sales_total
    active.cash_sales = cash_sales_total
    active.credit_sales = max(0.0, sales_total - cash_sales_total)
    active.total_expenses = expenses_total
    active.is_active = False
    active.notes = notes
    db.commit()
    db.refresh(active)
    return {"message": "Session closed", "session": _session_to_dict(active)}


@router.get("/current")
def get_current_session(
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    active = (
        db.query(SessionModel)
        .filter(SessionModel.is_active == True, SessionModel.shop_id == shop_id)
        .first()
    )
    if not active:
        return {"detail": "No active session"}
    return _session_to_dict(active)


@router.get("/current/summary")
def get_current_session_summary(
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    """Live-computed summary for the currently active session."""
    active = (
        db.query(SessionModel)
        .filter(SessionModel.is_active == True, SessionModel.shop_id == shop_id)
        .first()
    )
    if not active:
        raise HTTPException(status_code=404, detail="No active session")

    sales_q = db.query(Sale).filter(
        Sale.session_id == active.id,
        Sale.shop_id == shop_id,
    )
    all_sales = sales_q.all()
    active_sales = [s for s in all_sales if not s.is_voided]
    voided_sales = [s for s in all_sales if s.is_voided]

    cash_sales = sum((s.total_amount or 0) for s in active_sales if s.payment_status == "paid")
    credit_sales = sum(
        (s.total_amount or 0) for s in active_sales if s.payment_status in ("unpaid", "partial")
    )
    total_sales = sum((s.total_amount or 0) for s in active_sales)
    voided_amount = sum((s.total_amount or 0) for s in voided_sales)

    payments = (
        db.query(Payment).filter(Payment.session_id == active.id, Payment.shop_id == shop_id).all()
    )
    payments_total = sum(p.amount or 0 for p in payments)
    cash_payments = sum(p.amount or 0 for p in payments if (p.method or "cash").lower() == "cash")
    mobile_payments = sum(
        p.amount or 0
        for p in payments
        if (p.method or "").lower() in ("airtel_money", "tnm_mpamba", "mobile_money")
    )

    expenses_total = (
        db.query(Expense)
        .filter(Expense.session_id == active.id, Expense.shop_id == shop_id)
        .with_entities(func.sum(Expense.amount))
        .scalar()
        or 0
    )
    expenses_count = (
        db.query(Expense)
        .filter(Expense.session_id == active.id, Expense.shop_id == shop_id)
        .count()
    )

    opening = active.opening_balance or 0
    cash_added = active.cash_added or 0
    cash_removed = active.cash_removed or 0

    expected_in_drawer = (
        opening + cash_sales + cash_payments + cash_added - expenses_total - cash_removed
    )

    return {
        "session_id": active.id,
        "opened_at": active.opened_at,
        "opening_balance": opening,
        "sales": {
            "total_count": len(active_sales),
            "cash_sales": round(cash_sales, 2),
            "credit_sales": round(credit_sales, 2),
            "total_sales": round(total_sales, 2),
            "voided_count": len(voided_sales),
            "voided_amount": round(voided_amount, 2),
        },
        "payments_received": {
            "count": len(payments),
            "total": round(payments_total, 2),
            "cash": round(cash_payments, 2),
            "mobile_money": round(mobile_payments, 2),
        },
        "expenses": {
            "count": expenses_count,
            "total": round(expenses_total, 2),
        },
        "cash_drawer": {
            "opening_balance": round(opening, 2),
            "plus_cash_sales": round(cash_sales, 2),
            "plus_cash_payments_received": round(cash_payments, 2),
            "plus_cash_added": round(cash_added, 2),
            "minus_expenses": round(expenses_total, 2),
            "minus_cash_removed": round(cash_removed, 2),
            "expected_in_drawer": round(expected_in_drawer, 2),
        },
        "computed_at": datetime.utcnow().isoformat(),
    }


@router.get("/")
def get_sessions(
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    sessions = (
        db.query(SessionModel)
        .filter(SessionModel.shop_id == shop_id)
        .order_by(SessionModel.opened_at.desc())
        .all()
    )
    return [_session_to_dict(s) for s in sessions]
