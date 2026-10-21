"""Sessions (daily shift) API routes."""

from datetime import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models.session import Session as SessionModel
from app.db.models.sale import Sale
from app.db.models.expense import Expense
from app.api.dependencies import get_current_shop_id
from app.api.deps import require_min_role           # 🔧 Fix 2.5

router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.post("/open")
def open_session(
    opening_balance: float = Query(0.0),
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    """Open a new session (daily shift). Any authenticated user can open."""
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
    return new_session


@router.post(
    "/close",
    dependencies=[Depends(require_min_role("manager"))],  # 🔧 Fix 2.5
)
def close_session(
    closing_balance: float,
    notes: str = None,
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    """Close the active session.

    Requires manager or owner — affects end-of-day cash reconciliation.
    """
    active = (
        db.query(SessionModel)
        .filter(SessionModel.is_active == True, SessionModel.shop_id == shop_id)
        .first()
    )
    if not active:
        raise HTTPException(status_code=404, detail="No active session")

    # Calculate totals from linked sales and expenses
    sales_total = (
        db.query(Sale)
        .filter(Sale.session_id == active.id, Sale.shop_id == shop_id)
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
    active.total_expenses = expenses_total
    active.is_active = False
    active.notes = notes
    db.commit()
    return {"message": "Session closed", "session": active}


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
    return active or {"detail": "No active session"}


@router.get("/")
def get_sessions(
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    return (
        db.query(SessionModel)
        .filter(SessionModel.shop_id == shop_id)
        .order_by(SessionModel.opened_at.desc())
        .all()
    )