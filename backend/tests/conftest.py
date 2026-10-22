"""
Shared pytest fixtures.

Strategy: single shared test DB file. Each test clears all rows at teardown.

IMPORTANT: We DO NOT reload app modules or manipulate sys.path after import —
that breaks FastAPI's app object. Instead, we set env vars BEFORE importing
anything from `app`, and we assert we got the right object.
"""

import os
import tempfile
from pathlib import Path

import pytest

# ── MUST set env BEFORE importing app ──
_TEST_DB = Path(tempfile.gettempdir()) / "phindu_test.db"
if _TEST_DB.exists():
    _TEST_DB.unlink()

os.environ["SECRET_KEY"] = "test-secret-key-for-pytest-only-not-for-production"
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB.as_posix()}"

# ── Now import app modules ──
import app.db.models  # noqa: F401,E402
import app.main  # noqa: E402
from app.db.session import Base, SessionLocal, engine  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

# ── Guard rail: fail fast if the import is wrong ──
_fastapi_app = getattr(app.main, "app", None)
if not isinstance(_fastapi_app, FastAPI):
    raise RuntimeError(
        f"\n\n"
        f"conftest.py imported 'app.main' but 'app.main.app' is not a FastAPI instance.\n"
        f"  Got: {type(_fastapi_app)}\n"
        f"  app.main.__file__ = {getattr(app.main, '__file__', 'N/A')}\n"
        f"\n"
        f"Likely cause: `app/main.py` failed to fully load (import error or exception\n"
        f"during module execution). Scroll up in the pytest output for the original\n"
        f"traceback from `import app.main`.\n"
    )


@pytest.fixture(scope="session", autouse=True)
def _create_schema_once():
    """Create all tables once for the whole test session."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture(scope="function", autouse=True)
def _clean_tables():
    """Before each test, wipe all rows (keep schema). FK-safe order."""
    from app.db.models.customer import Customer
    from app.db.models.expense import Expense
    from app.db.models.payment import Payment
    from app.db.models.price_history import PriceHistory
    from app.db.models.product import Product
    from app.db.models.sale import Sale, SaleItem
    from app.db.models.session import Session as SessionModel
    from app.db.models.shop import Shop
    from app.db.models.stock import StockBatch
    from app.db.models.user import User

    db = SessionLocal()
    try:
        for model in [
            SaleItem,
            Sale,
            Payment,
            Expense,
            StockBatch,
            PriceHistory,
            Product,
            Customer,
            SessionModel,
            User,
            Shop,
        ]:
            db.query(model).delete()
        db.commit()
    finally:
        db.close()
    yield


@pytest.fixture(scope="function")
def app_client():
    """TestClient bound to the app (guarded above)."""
    with TestClient(_fastapi_app) as client:
        yield client


@pytest.fixture(scope="function")
def owner_client(app_client):
    """Authenticated as owner."""
    res = app_client.post(
        "/auth/register",
        json={
            "shop_name": "Test Shop",
            "full_name": "Test Owner",
            "email": "owner@test.com",
            "password": "test1234",
        },
    )
    assert res.status_code == 201, res.text
    token = res.json()["access_token"]
    app_client.headers["Authorization"] = f"Bearer {token}"
    yield app_client
    app_client.headers.pop("Authorization", None)


@pytest.fixture(scope="function")
def cashier_client(app_client, owner_client):
    """Cashier in the same shop as owner."""
    import uuid

    from app.core.security import get_password_hash
    from app.db.models.user import User

    db = SessionLocal()
    try:
        owner = db.query(User).filter(User.email == "owner@test.com").first()
        cashier = User(
            id=str(uuid.uuid4()),
            shop_id=owner.shop_id,
            email="cashier@test.com",
            hashed_password=get_password_hash("test1234"),
            full_name="Test Cashier",
            role="cashier",
            is_active=True,
        )
        db.add(cashier)
        db.commit()
    finally:
        db.close()

    res = app_client.post(
        "/auth/login",
        data={"username": "cashier@test.com", "password": "test1234"},
    )
    assert res.status_code == 200, res.text
    token = res.json()["access_token"]
    app_client.headers["Authorization"] = f"Bearer {token}"
    yield app_client
    app_client.headers.pop("Authorization", None)


@pytest.fixture(scope="function")
def sample_product(owner_client):
    res = owner_client.post(
        "/products/",
        json={
            "name": "Test Sugar",
            "category": "Food",
            "type": "variant",
            "unit": "piece",
            "selling_price": 1000.0,
            "purchase_price": 700.0,
            "stock_qty": 50,
        },
    )
    assert res.status_code == 200, res.text
    return res.json()


@pytest.fixture(scope="function")
def sample_customer(owner_client):
    res = owner_client.post(
        "/customers/",
        json={"name": "John Banda", "phone": "0999123456"},
    )
    assert res.status_code == 200, res.text
    return res.json()
