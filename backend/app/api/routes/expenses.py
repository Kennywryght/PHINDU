import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_serializer
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_shop_id
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


@router.get("/", response_model=list[ExpenseOut])
def get_expenses(
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    return (
        db.query(Expense)
        .filter(Expense.shop_id == shop_id)
        .order_by(Expense.created_at.desc())
        .all()
    )
