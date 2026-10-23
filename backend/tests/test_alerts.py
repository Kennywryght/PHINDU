"""Tests for alerts endpoints."""

from datetime import datetime, timedelta


# ── Helpers (defined once) ───────────────────────────────────────
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


def _make_sale(client, product_id, qty):
    """Create a sale with the given product quantity."""
    return client.post(
        "/sales/",
        json={"items": [{"product_id": product_id, "quantity": qty}]},
    )


# ── Low Stock ────────────────────────────────────────────────────
def test_low_stock_empty(owner_client):
    res = owner_client.get("/alerts/low-stock")
    assert res.status_code == 200
    assert res.json() == []


def test_low_stock_returns_below_threshold(owner_client):
    _make_product(owner_client, name="Low Item", stock_qty=3, low_stock_threshold=5)
    _make_product(owner_client, name="Fine Item", stock_qty=10, low_stock_threshold=5)

    res = owner_client.get("/alerts/low-stock")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["name"] == "Low Item"


def test_low_stock_severity_classification(owner_client):
    _make_product(owner_client, name="Out", stock_qty=0, low_stock_threshold=10)
    _make_product(owner_client, name="Critical", stock_qty=3, low_stock_threshold=10)
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
    owner_client.post(
        "/sales/",
        json={
            "items": [{"product_id": sample_product["id"], "quantity": 2}],
            "customer_id": sample_customer["id"],
            "payment_status": "unpaid",
        },
    )

    res = owner_client.get("/alerts/debtors?days=1")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1
    debtor = next((d for d in data if d["id"] == sample_customer["id"]), None)
    assert debtor is not None
    assert debtor["total_credit"] > 0
    assert debtor["never_paid"] is True


def test_debtors_excludes_recent_payment(owner_client, sample_customer, sample_product):
    owner_client.post(
        "/sales/",
        json={
            "items": [{"product_id": sample_product["id"], "quantity": 2}],
            "customer_id": sample_customer["id"],
            "payment_status": "unpaid",
        },
    )
    owner_client.post(
        f"/customers/{sample_customer['id']}/record-payment",
        json={"amount": 100, "method": "cash"},
    )

    res = owner_client.get("/alerts/debtors?days=14")
    data = res.json()
    assert not any(d["id"] == sample_customer["id"] for d in data)


# ── Slow Movers ──────────────────────────────────────────────────
def test_slow_movers_empty(owner_client):
    res = owner_client.get("/alerts/slow-movers")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)


def test_slow_movers_shows_never_sold(owner_client):
    _make_product(owner_client, name="Never Sold", stock_qty=20)

    res = owner_client.get("/alerts/slow-movers?days=1")
    assert res.status_code == 200
    data = res.json()
    assert any(p["name"] == "Never Sold" and p["never_sold"] is True for p in data)


def test_slow_movers_excludes_recent_sale(owner_client, sample_product):
    owner_client.post(
        "/sales/",
        json={"items": [{"product_id": sample_product["id"], "quantity": 1}]},
    )

    res = owner_client.get("/alerts/slow-movers?days=30")
    data = res.json()
    assert not any(p["id"] == sample_product["id"] for p in data)


def test_slow_movers_excludes_parent_products(owner_client):
    parent_res = _make_product(
        owner_client,
        name="Sugar",
        stock_qty=0,
        low_stock_threshold=0,
    )
    parent_id = parent_res.json()["id"]

    _make_product(
        owner_client,
        name="Sugar 1kg",
        stock_qty=50,
        parent_id=parent_id,
    )

    res = owner_client.get("/alerts/slow-movers?days=1")
    data = res.json()
    assert not any(p["id"] == parent_id for p in data)


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
    _make_product(owner_client, name="Low", stock_qty=1, low_stock_threshold=10)

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
    assert cashier_client.get("/alerts/low-stock").status_code == 200
    assert cashier_client.get("/alerts/debtors").status_code == 200
    assert cashier_client.get("/alerts/slow-movers").status_code == 200
    assert cashier_client.get("/alerts/summary").status_code == 200


# ─── REORDER SUGGESTIONS TESTS ───────────────────────────────────
# NOTE: _make_product and _make_sale are now defined ONCE at the top.
# The duplicated re-definitions that used to live here have been removed.


def test_reorder_empty_shop(owner_client):
    res = owner_client.get("/alerts/reorder-suggestions")
    assert res.status_code == 200
    data = res.json()
    assert data["critical"] == []
    assert data["soon"] == []
    assert data["ok"] == []
    assert data["no_data"] == []


def test_reorder_no_sales_goes_to_no_data(owner_client):
    _make_product(owner_client, name="Fresh Stock", stock_qty=50)

    res = owner_client.get("/alerts/reorder-suggestions")
    data = res.json()

    assert len(data["no_data"]) >= 1
    assert any(p["name"] == "Fresh Stock" for p in data["no_data"])
    assert not any(p["name"] == "Fresh Stock" for p in data["critical"])
    assert not any(p["name"] == "Fresh Stock" for p in data["soon"])
    assert not any(p["name"] == "Fresh Stock" for p in data["ok"])


def test_reorder_zero_stock_is_critical(owner_client):
    res = _make_product(owner_client, name="Sold Out Item", stock_qty=5)
    product_id = res.json()["id"]

    _make_sale(owner_client, product_id, 5)

    res = owner_client.get("/alerts/reorder-suggestions")
    data = res.json()

    critical_items = [p["name"] for p in data["critical"]]
    assert "Sold Out Item" in critical_items


def test_reorder_fast_mover_is_critical(owner_client):
    res = _make_product(owner_client, name="Fast Mover", stock_qty=50)
    product_id = res.json()["id"]

    _make_sale(owner_client, product_id, 40)

    res = owner_client.get("/alerts/reorder-suggestions")
    data = res.json()

    all_products = data["critical"] + data["soon"] + data["ok"]
    found = [p for p in all_products if p["name"] == "Fast Mover"]
    assert len(found) == 1
    p = found[0]

    assert p["units_sold_last_period"] == 40
    assert p["avg_daily_sales"] > 0


def test_reorder_suggests_7_day_supply(owner_client):
    res = _make_product(owner_client, name="Steady Seller", stock_qty=100)
    product_id = res.json()["id"]

    _make_sale(owner_client, product_id, 30)

    res = owner_client.get("/alerts/reorder-suggestions?target_days=7")
    data = res.json()

    all_products = data["critical"] + data["soon"] + data["ok"]
    p = next(x for x in all_products if x["name"] == "Steady Seller")

    assert p["suggested_order_qty"] == 7


def test_reorder_confidence_levels(owner_client):
    res = _make_product(owner_client, name="Low Conf", stock_qty=50)
    _make_sale(owner_client, res.json()["id"], 5)

    res = _make_product(owner_client, name="Med Conf", stock_qty=50)
    _make_sale(owner_client, res.json()["id"], 20)

    res = _make_product(owner_client, name="High Conf", stock_qty=50)
    _make_sale(owner_client, res.json()["id"], 50)

    res = owner_client.get("/alerts/reorder-suggestions")
    data = res.json()
    all_products = data["critical"] + data["soon"] + data["ok"]

    low = next(p for p in all_products if p["name"] == "Low Conf")
    med = next(p for p in all_products if p["name"] == "Med Conf")
    high = next(p for p in all_products if p["name"] == "High Conf")

    assert low["confidence"] == "low"
    assert med["confidence"] == "medium"
    assert high["confidence"] == "high"


def test_reorder_excludes_parent_products(owner_client):
    parent_res = _make_product(
        owner_client, name="Parent", stock_qty=0, selling_price=0, purchase_price=0
    )
    parent_id = parent_res.json()["id"]

    _make_product(owner_client, name="Variant", stock_qty=10, parent_id=parent_id)

    res = owner_client.get("/alerts/reorder-suggestions")
    data = res.json()

    all_names = [
        p["name"]
        for p in (data["critical"] + data["soon"] + data["ok"] + data["no_data"])
    ]
    assert "Parent" not in all_names
    assert "Variant" in all_names


def test_reorder_shop_scoped(owner_client, app_client):
    _make_product(owner_client, name="Shop A Item", stock_qty=50)

    app_client.post(
        "/auth/register",
        json={
            "shop_name": "Shop B",
            "full_name": "Owner B",
            "email": "owner-b-reorder@test.com",
            "password": "test1234",
        },
    )
    token_b = app_client.post(
        "/auth/login",
        data={"username": "owner-b-reorder@test.com", "password": "test1234"},
    ).json()["access_token"]

    res = app_client.get(
        "/alerts/reorder-suggestions",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    data = res.json()

    assert data["critical"] == []
    assert data["soon"] == []
    assert data["ok"] == []
    assert data["no_data"] == []