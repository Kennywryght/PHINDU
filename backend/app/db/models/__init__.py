# Database models package
"""
Import ALL models here so `import app.db.models` registers every table
with Base.metadata. Alembic's autogenerate depends on this.
"""

from app.db.models.customer import Customer
from app.db.models.expense import Expense
from app.db.models.payment import Payment  # 🔧 NEW in Sprint 3.2
from app.db.models.price_history import PriceHistory
from app.db.models.product import Product
from app.db.models.sale import Sale, SaleItem
from app.db.models.session import Session
from app.db.models.shop import Shop
from app.db.models.stock import StockBatch
from app.db.models.user import User

__all__ = [
    "User",
    "Shop",
    "Product",
    "StockBatch",
    "Customer",
    "Sale",
    "SaleItem",
    "Expense",
    "Session",
    "PriceHistory",
    "Payment",
]
