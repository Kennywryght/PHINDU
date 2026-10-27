"""Expense API routes."""

import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_serializer
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_shop_id
from app.api.deps import require_min_role
from app.db.models.expense import Expense
from app.db.models.session import Session as SessionModel
from app.db.session import SessionLocal

router = APIRouter(prefix="/expenses", tags=["Expenses"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ExpenseCreate(BaseModel):
    name: str = Field(..., min_length=1)
    amount: float = Field(..., gt=0)
    category: str = Field(..., min_length=1)


class ExpenseUpdate(BaseModel):
    name: str | None = Field(None, min_length=1)
    amount: float | None = Field(None, gt=0)
    category: str | None = Field(None, min_length=1)


class ExpenseOut(BaseModel):
    id: str
    name: str
    amount: float
    category: str
    shop_id: str | None = None
    session_id: str | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True

    @field_serializer("created_at")
    def serialize_created_at(self, dt: datetime | None, _info):
        return dt.isoformat() if dt else None


@router.post("/", response_model=ExpenseOut)
def create_expense(
    data: ExpenseCreate,
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    active_session = (
        db.query(SessionModel)
        .filter(
            SessionModel.is_active == True,
            SessionModel.shop_id == shop_id,
        )
        .first()
    )

    expense = Expense(
        id=str(uuid.uuid4()),
        name=data.name,
        amount=data.amount,
        category=data.category,
        shop_id=shop_id,
        session_id=active_session.id if active_session else None,
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


@router.get("/summary")
def expenses_summary(
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=6)
    month_start = today_start - timedelta(days=29)

    def _sum_since(since: datetime) -> float:
        return float(
            db.query(func.coalesce(func.sum(Expense.amount), 0))
            .filter(Expense.shop_id == shop_id, Expense.created_at >= since)
            .scalar()
            or 0
        )

    total = float(
        db.query(func.coalesce(func.sum(Expense.amount), 0))
        .filter(Expense.shop_id == shop_id)
        .scalar()
        or 0
    )
    count = (
        db.query(func.count(Expense.id))
        .filter(Expense.shop_id == shop_id)
        .scalar()
        or 0
    )

    cat_rows = (
        db.query(Expense.category, func.sum(Expense.amount).label("total"))
        .filter(Expense.shop_id == shop_id)
        .group_by(Expense.category)
        .order_by(func.sum(Expense.amount).desc())
        .limit(5)
        .all()
    )
    top_categories = [
        {"category": r.category or "Uncategorized", "total": float(r.total or 0)}
        for r in cat_rows
    ]

    return {
        "total": round(total, 2),
        "today": round(_sum_since(today_start), 2),
        "this_week": round(_sum_since(week_start), 2),
        "this_month": round(_sum_since(month_start), 2),
        "count": int(count),
        "top_categories": top_categories,
    }


@router.get("/", response_model=dict)
def get_expenses(
    q: str | None = Query(None),
    category: str | None = Query(None),
    days: int | None = Query(None, ge=1, le=365),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    base = db.query(Expense).filter(Expense.shop_id == shop_id)

    if days is not None:
        cutoff = datetime.utcnow() - timedelta(days=days)
        base = base.filter(Expense.created_at >= cutoff)

    if category:
        base = base.filter(func.lower(Expense.category) == category.strip().lower())

    if q:
        like = f"%{q.strip()}%"
        base = base.filter(
            (Expense.name.ilike(like)) | (Expense.category.ilike(like))
        )

    total = base.count()
    items = (
        base.order_by(Expense.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "items": [
            {
                "id": e.id,
                "name": e.name,
                "amount": float(e.amount or 0),
                "category": e.category,
                "shop_id": e.shop_id,
                "session_id": e.session_id,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in items
        ],
        "total": total,
        "has_more": offset + len(items) < total,
    }


@router.get("/categories")
def list_categories(
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    rows = (
        db.query(Expense.category, func.count(Expense.id).label("count"))
        .filter(
            Expense.shop_id == shop_id,
            Expense.category.isnot(None),
            Expense.category != "",
        )
        .group_by(Expense.category)
        .order_by(Expense.category)
        .all()
    )
    return [
        {"name": r.category, "count": int(r.count or 0)}
        for r in rows
        if r.category
    ]


@router.put(
    "/{expense_id}",
    response_model=ExpenseOut,
    dependencies=[Depends(require_min_role("manager"))],
)
def update_expense(
    expense_id: str,
    data: ExpenseUpdate,
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    expense = (
        db.query(Expense)
        .filter(Expense.id == expense_id, Expense.shop_id == shop_id)
        .first()
    )
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(expense, field, value)

    db.commit()
    db.refresh(expense)
    return expense


@router.delete(
    "/{expense_id}",
    dependencies=[Depends(require_min_role("manager"))],
)
def delete_expense(
    expense_id: str,
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    expense = (
        db.query(Expense)
        .filter(Expense.id == expense_id, Expense.shop_id == shop_id)
        .first()
    )
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    db.delete(expense)
    db.commit()
    return {"message": "Expense deleted"}


@router.get("/{expense_id}", response_model=ExpenseOut)
def get_expense(
    expense_id: str,
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    expense = (
        db.query(Expense)
        .filter(Expense.id == expense_id, Expense.shop_id == shop_id)
        .first()
    )
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    return expense