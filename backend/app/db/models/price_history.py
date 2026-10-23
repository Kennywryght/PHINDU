import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, String

from app.db.session import Base


class PriceHistory(Base):
    __tablename__ = "price_history"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    product_id = Column(String, ForeignKey("products.id"), nullable=False)

    old_price = Column(Float)
    new_price = Column(Float)

    # 🔧 NEW: distinguishes selling vs purchase price changes
    # "selling" (default for existing rows) or "purchase"
    price_type = Column(String, default="selling", nullable=False)

    changed_at = Column(DateTime, default=datetime.utcnow)