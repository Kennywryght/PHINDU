"""
Payment model — audit trail for every credit payment received from a customer.

This table is used TODAY for customer credit payments (John owes 5000, pays 2000).
In Sprint 10+ it will be extended with `direction` and `subscription_id` columns
for premium subscription payments (shop owner pays for app features).
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import relationship

from app.db.session import Base


class Payment(Base):
    __tablename__ = "payments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    shop_id = Column(String, ForeignKey("shops.id"), nullable=False)
    customer_id = Column(String, ForeignKey("customers.id"), nullable=False)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=True)
    sale_id = Column(String, ForeignKey("sales.id"), nullable=True)

    amount = Column(Float, nullable=False)
    # cash, airtel_money, tnm_mpamba, bank, cheque, other
    method = Column(String, default="cash", nullable=False)
    note = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # ── Relationships ────────────────────────────────────────────
    shop = relationship("Shop", back_populates="payments")
    customer = relationship("Customer", back_populates="payments")
    session = relationship("Session", back_populates="payments")
    sale = relationship("Sale", back_populates="payments")
