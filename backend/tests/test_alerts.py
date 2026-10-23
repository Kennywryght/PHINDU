"""Tests for alerts endpoints."""

from datetime import datetime, timedelta


def _make_product(client, **overrides):
    payload = {
        "name": "Test Product",
        "category": "Test",
        "type": "variant",
        "unit": "piece",
        "selling_price": 1000.0,
        "purchase_price": 700.0,
        "stock_qty": 10,
    }
    payload.update(overrides)
    return client.post("/products/", json=payload)


# ── Low Stock ────────────────────────────────────────────────────
def test_low_stock_empty(owner_client):
    res = owner_client.get("/alerts/low-stock")
    assert res.status_code == 200
    assert res.json() == []


def test_low_stock_returns_below_threshold(owner_client):
    # Product with stock 3, default threshold 5 → below
    _make_product(owner_client, name="Low Item", stock_qty=3, low_stock_threshold=5)
    # Product with stock 10, threshold 5 → fine
    _make_product(owner_client, name="Fine Item", stock_qty=10, low_stock_threshold=5)

    res = owner_client.get("/alerts/low-stock")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["name"] == "Low Item"


def test_low_stock_severity_classification(owner_client):
    # Out of stock (stock = 0)
    _make_product(owner_client, name="Out", stock_qty=0, low_stock_threshold=10)
    # Critical (stock <= threshold * 0.4 = 4)
    _make_product(owner_client, name="Critical", stock_qty=3, low_stock_threshold=10)
    # Low (stock above critical but <= threshold)
    _make_product(owner_client, name="Low", stock_qty=8, low_stock_threshold=10)

    res = owner_client.get("/alerts/low-stock")
    data = res.json()

    severities = {p["name"]: p["severity"] for p in data}
    assert severities["Out"] == "out_of_stock"
    assert severities["Critical"] == "critical"
    assert severities["Low"] == "low"


def test_low_stock_excludes_deleted(owner_client):
    res = _make_product(owner_client, name="Deleted", stock_qty=1, low_stock_threshold=10)
    product_id = res.json()["id"]
    owner_client.delete(f"/products/{product_id}")

    res = owner_client.get("/alerts/low-stock")
    assert not any(p["name"] == "Deleted" for p in res.json())


# ── Debtors ──────────────────────────────────────────────────────
def test_debtors_empty(owner_client):
    res = owner_client.get("/alerts/debtors")
    assert res.status_code == 200
    assert res.json() == []


def test_debtors_shows_customer_with_credit(owner_client, sample_customer, sample_product):
    # Create a credit sale to give customer debt
    owner_client.post(
        "/sales/",
        json={
            "items": [{"product_id": sample_product["id"], "quantity": 2}],
            "customer_id": sample_customer["id"],
            "payment_status": "unpaid",
        },
    )

    # Customer now owes money. But their "last payment" is None, so they should show
    res = owner_client.get("/alerts/debtors?days=1")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1
    debtor = next((d for d in data if d["id"] == sample_customer["id"]), None)
    assert debtor is not None
    assert debtor["total_credit"] > 0
    assert debtor["never_paid"] is True


def test_debtors_excludes_recent_payment(owner_client, sample_customer, sample_product):
    # Create credit sale
    owner_client.post(
        "/sales/",
        json={
            "items": [{"product_id": sample_product["id"], "quantity": 2}],
            "customer_id": sample_customer["id"],
            "payment_status": "unpaid",
        },
    )
    # Record a payment (just now)
    owner_client.post(
        f"/customers/{sample_customer['id']}/record-payment",
        json={"amount": 100, "method": "cash"},
    )

    # Query with days=14 — payment is today, so this customer should NOT appear
    res = owner_client.get("/alerts/debtors?days=14")
    data = res.json()
    assert not any(d["id"] == sample_customer["id"] for d in data)


# ── Slow Movers ──────────────────────────────────────────────────
def test_slow_movers_empty(owner_client):
    res = owner_client.get("/alerts/slow-movers")
    assert res.status_code == 200
    # New products have never been sold, so this will return them
    # But if no products exist, empty
    data = res.json()
    # Empty if no in-stock products; otherwise they're "never sold"
    assert isinstance(data, list)


def test_slow_movers_shows_never_sold(owner_client):
    _make_product(owner_client, name="Never Sold", stock_qty=20)

    res = owner_client.get("/alerts/slow-movers?days=1")
    assert res.status_code == 200
    data = res.json()
    assert any(p["name"] == "Never Sold" and p["never_sold"] is True for p in data)


def test_slow_movers_excludes_recent_sale(owner_client, sample_product):
    # sample_product comes with stock_qty=50
    # Make a sale today
    owner_client.post(
        "/sales/",
        json={"items": [{"product_id": sample_product["id"], "quantity": 1}]},
    )

    # Query with days=30 — sale is today, so it should NOT appear
    res = owner_client.get("/alerts/slow-movers?days=30")
    data = res.json()
    assert not any(p["id"] == sample_product["id"] for p in data)


def test_slow_movers_excludes_parent_products(owner_client):
    # Create parent
    parent_res = _make_product(
        owner_client,
        name="Sugar",
        stock_qty=0,
        low_stock_threshold=0,
    )
    parent_id = parent_res.json()["id"]

    # Create variant with stock
    _make_product(
        owner_client,
        name="Sugar 1kg",
        stock_qty=50,
        parent_id=parent_id,
    )

    res = owner_client.get("/alerts/slow-movers?days=1")
    data = res.json()
    # Parent should NOT appear (parent_id is None only for real products)
    assert not any(p["id"] == parent_id for p in data)
    # Variant may appear (never sold)


# ── Summary ──────────────────────────────────────────────────────
def test_summary_all_zero(owner_client):
    res = owner_client.get("/alerts/summary")
    assert res.status_code == 200
    data = res.json()
    assert data["low_stock"] == 0
    assert data["debtors"] == 0
    assert data["slow_movers"] == 0
    assert data["total"] == 0


def test_summary_counts_correctly(owner_client, sample_customer, sample_product):
    # Low stock product
    _make_product(owner_client, name="Low", stock_qty=1, low_stock_threshold=10)

    # Credit sale for debtor
    owner_client.post(
        "/sales/",
        json={
            "items": [{"product_id": sample_product["id"], "quantity": 1}],
            "customer_id": sample_customer["id"],
            "payment_status": "unpaid",
        },
    )

    res = owner_client.get("/alerts/summary")
    data = res.json()
    assert data["low_stock"] >= 1
    assert data["debtors"] >= 1
    assert data["total"] >= 2


# ── Role enforcement ─────────────────────────────────────────────
def test_alerts_accessible_to_any_role(cashier_client):
    """All alert endpoints should be readable by any authenticated user."""
    assert cashier_client.get("/alerts/low-stock").status_code == 200
    assert cashier_client.get("/alerts/debtors").status_code == 200
    assert cashier_client.get("/alerts/slow-movers").status_code == 200
    assert cashier_client.get("/alerts/summary").status_code == 200