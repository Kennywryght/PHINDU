import uuid

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    shop_id = Column(String, ForeignKey("shops.id"), nullable=False)
    opened_at = Column(DateTime, server_default=func.now())
    closed_at = Column(DateTime, nullable=True)
    opening_balance = Column(Float, default=0.0)
    closing_balance = Column(Float, nullable=True)
    total_sales = Column(Float, default=0.0)
    total_expenses = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    notes = Column(String, nullable=True)

    # ── Sprint 3.1 fields ──────────────────────────────────────
    cash_sales = Column(Float, default=0.0)
    credit_sales = Column(Float, default=0.0)
    cash_removed = Column(Float, default=0.0)
    cash_added = Column(Float, default=0.0)

    # ── Reconciliation (Session deep-dive) ─────────────────────
    # Frozen snapshot at close — so past reports stay accurate even if
    # the underlying data is later edited (e.g. an expense is voided).
    expected_closing_balance = Column(Float, nullable=True)
    # positive = OVER (drawer has more than expected)
    # negative = SHORT (drawer has less than expected)
    # null     = session still open or reconciliation skipped
    cash_discrepancy = Column(Float, nullable=True)
    discrepancy_reason = Column(String, nullable=True)

    # Relationships
    shop = relationship("Shop", back_populates="sessions")
    sales = relationship("Sale", back_populates="session")
    payments = relationship("Payment", back_populates="session")