"""Tests for dashboard + revenue-trend day-range support."""

from datetime import datetime, timedelta


def _make_product(client, **overrides):
    payload = {
        "name": "Trend Product",
        "category": "Test",
        "type": "variant",
        "unit": "piece",
        "selling_price": 1000.0,
        "purchase_price": 700.0,
        "stock_qty": 50,
    }
    payload.update(overrides)
    return client.post("/products/", json=payload)


def _make_sale(client, product_id, qty=1):
    return client.post(
        "/sales/",
        json={"items": [{"product_id": product_id, "quantity": qty}]},
    )


# ─── /analytics/revenue-trend ────────────────────────────────────


def test_revenue_trend_default_7_days(owner_client):
    """No ?days → exactly 7 entries, oldest first."""
    res = owner_client.get("/analytics/revenue-trend")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) == 7
    # Each entry has date + revenue
    for row in data:
        assert "date" in row
        assert "revenue" in row
        assert isinstance(row["revenue"], float)
    # Oldest first → dates strictly increasing
    dates = [row["date"] for row in data]
    assert dates == sorted(dates)


def test_revenue_trend_14_days(owner_client):
    res = owner_client.get("/analytics/revenue-trend?days=14")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 14


def test_revenue_trend_30_days(owner_client):
    res = owner_client.get("/analytics/revenue-trend?days=30")
    assert res.status_code == 200
    assert len(res.json()) == 30


def test_revenue_trend_1_day(owner_client):
    res = owner_client.get("/analytics/revenue-trend?days=1")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    # Should be today (UTC)
    assert data[0]["date"] == datetime.utcnow().date().isoformat()


def test_revenue_trend_rejects_invalid_days(owner_client):
    """days must be 1..90."""
    assert owner_client.get("/analytics/revenue-trend?days=0").status_code == 422
    assert owner_client.get("/analytics/revenue-trend?days=91").status_code == 422
    assert owner_client.get("/analytics/revenue-trend?days=-3").status_code == 422


def test_revenue_trend_includes_today_sale(owner_client):
    """A sale made today should show up in the last bucket of the trend."""
    prod = _make_product(owner_client, name="Today Sale", selling_price=500, stock_qty=10)
    pid = prod.json()["id"]

    sale = _make_sale(owner_client, pid, qty=2)
    assert sale.status_code in (200, 201)
    expected = sale.json()["total_amount"]  # 500 × 2 = 1000

    res = owner_client.get("/analytics/revenue-trend?days=7")
    data = res.json()
    today_iso = datetime.utcnow().date().isoformat()
    today_row = next((r for r in data if r["date"] == today_iso), None)
    assert today_row is not None
    assert today_row["revenue"] == float(expected)


def test_revenue_trend_shop_scoped(owner_client, app_client):
    """Shop B's trend should be all zeros even when Shop A has sales."""
    prod = _make_product(owner_client, name="Scoped Prod", selling_price=100, stock_qty=5)
    _make_sale(owner_client, prod.json()["id"], qty=1)

    app_client.post(
        "/auth/register",
        json={
            "shop_name": "Shop B",
            "full_name": "Owner B",
            "email": "owner-b-trend@test.com",
            "password": "test1234",
        },
    )
    token_b = app_client.post(
        "/auth/login",
        data={"username": "owner-b-trend@test.com", "password": "test1234"},
    ).json()["access_token"]

    res = app_client.get(
        "/analytics/revenue-trend?days=7",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res.status_code == 200
    assert all(row["revenue"] == 0.0 for row in res.json())


# ─── /dashboard/ still works (regression guard) ──────────────────


def test_dashboard_empty_shop(owner_client):
    res = owner_client.get("/dashboard/")
    assert res.status_code == 200
    data = res.json()
    assert data["total_revenue"] == 0
    assert data["profit"] == 0
    assert data["total_items_sold"] == 0


def test_dashboard_after_sale(owner_client):
    prod = _make_product(owner_client, name="Dash Prod", selling_price=1000, purchase_price=600, stock_qty=10)
    pid = prod.json()["id"]
    _make_sale(owner_client, pid, qty=2)

    res = owner_client.get("/dashboard/")
    assert res.status_code == 200
    data = res.json()
    assert data["total_revenue"] == 2000.0
    assert data["total_items_sold"] == 2
    assert data["profit"] > 0
    
# ─── BATCH 2: /dashboard/today ───────────────────────────────────


def test_today_empty_shop(owner_client):
    res = owner_client.get("/dashboard/today")
    assert res.status_code == 200
    data = res.json()
    assert data["revenue"] == 0.0
    assert data["profit"] == 0.0
    assert data["sales_count"] == 0
    assert data["low_stock_count"] == 0
    assert "date" in data


def test_today_reflects_today_sale(owner_client):
    prod = _make_product(owner_client, name="Today Prod", selling_price=500, purchase_price=300, stock_qty=20)
    pid = prod.json()["id"]
    _make_sale(owner_client, pid, qty=3)  # revenue = 1500

    res = owner_client.get("/dashboard/today")
    data = res.json()
    assert data["revenue"] == 1500.0
    assert data["sales_count"] == 1
    # profit = revenue - cost = 1500 - (300*3) = 600 (no expenses)
    assert data["profit"] == 600.0


def test_today_counts_low_stock(owner_client):
    # stock 3, threshold 5 → low
    _make_product(owner_client, name="Low A", stock_qty=3, low_stock_threshold=5)
    # stock 20, threshold 5 → fine
    _make_product(owner_client, name="Fine A", stock_qty=20, low_stock_threshold=5)

    res = owner_client.get("/dashboard/today")
    data = res.json()
    assert data["low_stock_count"] == 1


# ─── BATCH 2: /dashboard/health-score ────────────────────────────


def test_health_score_empty_shop(owner_client):
    res = owner_client.get("/dashboard/health-score")
    assert res.status_code == 200
    data = res.json()
    # No revenue → 0 profit-margin + 0 cash-flow points. No products → full stock pts.
    # No credit issued → full debt pts. So score should be 20 + 10 = 30.
    assert data["score"] == 30
    assert data["tone"] == "bad"
    assert "components" in data
    assert data["components"]["profit_margin_points"] == 0
    assert data["components"]["cash_flow_points"] == 0
    assert data["components"]["stock_points"] == 20
    assert data["components"]["debt_points"] == 10


def test_health_score_healthy_shop(owner_client):
    # Sell with healthy margin (60%): 1000 sell, 400 cost, stock plenty
    prod = _make_product(
        owner_client, name="Healthy Prod",
        selling_price=1000, purchase_price=400, stock_qty=100,
        low_stock_threshold=5,
    )
    pid = prod.json()["id"]
    _make_sale(owner_client, pid, qty=5)  # rev 5000, cost 2000, profit 3000 → margin 60%

    res = owner_client.get("/dashboard/health-score")
    data = res.json()
    # margin 60% → 40 pts; cash flow ratio 0.6 → 18 pts; stock: healthy → 20;
    # debt: no credit sold → full 10
    assert data["score"] >= 85
    assert data["tone"] == "good"
    assert data["components"]["profit_margin_points"] == 40


def test_health_score_has_delta_and_message(owner_client):
    res = owner_client.get("/dashboard/health-score")
    data = res.json()
    assert "delta" in data
    assert "previous" in data
    assert "message" in data
    assert isinstance(data["message"], str)
    assert data["label"] in ("Healthy", "Watch", "Needs attention")


# ─── BATCH 2: /dashboard/focus ───────────────────────────────────


def test_focus_empty_shop(owner_client):
    res = owner_client.get("/dashboard/focus")
    assert res.status_code == 200
    data = res.json()
    assert data["items"] == []
    assert "generated_at" in data


def test_focus_detects_critical_zero_stock(owner_client):
    # Create product with stock, sell all of it today
    prod = _make_product(owner_client, name="Sold Out", selling_price=500, stock_qty=5)
    pid = prod.json()["id"]
    _make_sale(owner_client, pid, qty=5)

    res = owner_client.get("/dashboard/focus")
    data = res.json()
    assert len(data["items"]) >= 1
    assert any(
        i["type"] == "critical" and "Sold Out" in i["title"]
        for i in data["items"]
    )


def test_focus_detects_overdue_debtor(owner_client):
    # Customer with unpaid sale and no payment recorded
    cust = owner_client.post("/customers/", json={"name": "Overdue Co"}).json()
    prod = _make_product(owner_client, name="Credit Prod", selling_price=500, stock_qty=50)
    pid = prod.json()["id"]

    owner_client.post(
        "/sales/",
        json={
            "items": [{"product_id": pid, "quantity": 2}],
            "customer_id": cust["id"],
            "payment_status": "unpaid",
        },
    )

    res = owner_client.get("/dashboard/focus")
    data = res.json()
    debtor_items = [i for i in data["items"] if i["type"] == "debtors"]
    assert len(debtor_items) == 1
    assert "debtor" in debtor_items[0]["title"].lower()


def test_focus_caps_at_three_items(owner_client):
    # Create 5 sold-out products + 1 debtor — should still cap at 3
    for i in range(5):
        prod = _make_product(owner_client, name=f"Sold{i}", selling_price=100, stock_qty=3)
        pid = prod.json()["id"]
        _make_sale(owner_client, pid, qty=3)

    res = owner_client.get("/dashboard/focus")
    data = res.json()
    assert len(data["items"]) <= 3
    
# ─── BATCH 3: /cash-flow ─────────────────────────────────────────


def test_cash_flow_empty_shop(owner_client):
    res = owner_client.get("/dashboard/cash-flow")
    assert res.status_code == 200
    data = res.json()
    assert data["cash_in"] == 0.0
    assert data["cash_out"] == 0.0
    assert data["net"] == 0.0
    assert data["drawer"] is None
    assert data["window_days"] == 7


def test_cash_flow_reflects_sale(owner_client):
    prod = _make_product(owner_client, name="CF Prod", selling_price=1000, purchase_price=600, stock_qty=20)
    pid = prod.json()["id"]
    _make_sale(owner_client, pid, qty=2)  # 2000 revenue, paid in cash by default

    res = owner_client.get("/dashboard/cash-flow?days=7")
    data = res.json()
    assert data["cash_in"] >= 2000.0
    assert data["breakdown"]["sales_paid"] >= 2000.0


def test_cash_flow_respects_days_param(owner_client):
    assert owner_client.get("/dashboard/cash-flow?days=30").status_code == 200
    assert owner_client.get("/dashboard/cash-flow?days=0").status_code == 422
    assert owner_client.get("/dashboard/cash-flow?days=91").status_code == 422


# ─── BATCH 3: /metric-deltas ─────────────────────────────────────


def test_metric_deltas_empty(owner_client):
    res = owner_client.get("/dashboard/metric-deltas")
    assert res.status_code == 200
    data = res.json()
    for key in ("revenue", "profit", "expenses", "items_sold"):
        assert key in data
        assert data[key]["current"] == 0.0
        assert data[key]["previous"] == 0.0
        assert data[key]["percent"] is None  # no prev, no cur


def test_metric_deltas_after_today_sale(owner_client):
    prod = _make_product(owner_client, name="Delta Prod", selling_price=500, purchase_price=300, stock_qty=20)
    pid = prod.json()["id"]
    _make_sale(owner_client, pid, qty=4)  # today: 2000 revenue

    res = owner_client.get("/dashboard/metric-deltas")
    data = res.json()
    assert data["revenue"]["current"] == 2000.0
    assert data["revenue"]["previous"] == 0.0
    assert data["revenue"]["percent"] == 100.0  # cur > 0, prev = 0
    assert data["items_sold"]["current"] == 4.0


# ─── BATCH 3: /top-products-trend ───────────────────────────────


def test_top_products_trend_empty(owner_client):
    res = owner_client.get("/dashboard/top-products-trend")
    assert res.status_code == 200
    data = res.json()
    assert data["products"] == []
    assert data["window_days"] == 7


def test_top_products_trend_has_sparkline(owner_client):
    prod = _make_product(owner_client, name="Spark Prod", selling_price=500, purchase_price=300, stock_qty=30)
    pid = prod.json()["id"]
    _make_sale(owner_client, pid, qty=3)

    res = owner_client.get("/dashboard/top-products-trend?days=7")
    data = res.json()
    assert len(data["products"]) == 1
    p = data["products"][0]
    assert p["name"] == "Spark Prod"
    assert p["quantity"] == 3.0
    assert len(p["sparkline"]) == 7
    # All quantities appear in the last (today's) bucket
    assert sum(p["sparkline"]) == 3.0


def test_top_products_trend_limits_results(owner_client):
    for i in range(5):
        prod = _make_product(owner_client, name=f"P{i}", selling_price=100, purchase_price=50, stock_qty=20)
        _make_sale(owner_client, prod.json()["id"], qty=i + 1)

    res = owner_client.get("/dashboard/top-products-trend?limit=3")
    data = res.json()
    assert len(data["products"]) == 3