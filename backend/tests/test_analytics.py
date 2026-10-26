"""Tests for analytics endpoints + cross-shop isolation."""


def test_insights_endpoint(owner_client, sample_product):
    res = owner_client.get("/analytics/insights")
    assert res.status_code == 200
    data = res.json()
    assert "total_products" in data
    assert "total_sales" in data
    assert data["total_products"] >= 1


def test_revenue_trend_returns_7_days(owner_client):
    """Default /revenue-trend returns 7 days (Batch 1 change)."""
    res = owner_client.get("/analytics/revenue-trend")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 7

    dates = [row["date"] for row in data]
    assert dates == sorted(dates)


def test_revenue_trend_includes_todays_sales(owner_client, sample_product):
    owner_client.post(
        "/sales/",
        json={"items": [{"product_id": sample_product["id"], "quantity": 2}]},
    )
    res = owner_client.get("/analytics/revenue-trend")
    data = res.json()
    assert data[-1]["revenue"] == 2000.0


def test_top_products_day(owner_client, sample_product):
    owner_client.post(
        "/sales/",
        json={"items": [{"product_id": sample_product["id"], "quantity": 3}]},
    )
    res = owner_client.get("/analytics/top-products?period=day")
    assert res.status_code == 200
    products = res.json()
    assert len(products) >= 1
    assert products[0]["quantity"] == 3


def test_profit_margins(owner_client, sample_product):
    """Sample product: sell 1000, cost 700 → 30% margin."""
    owner_client.post(
        "/sales/",
        json={"items": [{"product_id": sample_product["id"], "quantity": 2}]},
    )
    res = owner_client.get("/analytics/profit-margins")
    assert res.status_code == 200
    margins = res.json()
    product_margin = next(m for m in margins if m["id"] == sample_product["id"])

    assert product_margin["revenue"] == 2000.0
    assert product_margin["cost"] == 1400.0  # 700 × 2
    assert product_margin["profit"] == 600.0
    assert product_margin["margin_percent"] == 30.0


def test_peak_hours(owner_client, sample_product):
    owner_client.post(
        "/sales/",
        json={"items": [{"product_id": sample_product["id"], "quantity": 1}]},
    )
    res = owner_client.get("/analytics/peak-hours")
    assert res.status_code == 200
    data = res.json()
    assert "hours" in data
    assert len(data["hours"]) == 24
    # At least one hour has a sale
    assert sum(data["hours"]) >= 1


def test_expense_breakdown(owner_client):
    owner_client.post(
        "/expenses/",
        json={"name": "Tea", "amount": 300, "category": "Food"},
    )
    owner_client.post(
        "/expenses/",
        json={"name": "Lunch", "amount": 500, "category": "Food"},
    )
    owner_client.post(
        "/expenses/",
        json={"name": "Bus", "amount": 200, "category": "Transport"},
    )

    res = owner_client.get("/analytics/expense-breakdown")
    assert res.status_code == 200
    breakdown = {e["category"]: e["total"] for e in res.json()}
    assert breakdown["Food"] == 800.0
    assert breakdown["Transport"] == 200.0


def test_sell_speed(owner_client, sample_product):
    """Sell out stock → batch should be marked finished → sell-speed returns it."""
    # Sample product has stock_qty=50, sell all 50
    owner_client.post(
        "/sales/",
        json={"items": [{"product_id": sample_product["id"], "quantity": 50}]},
    )

    res = owner_client.get("/analytics/sell-speed")
    assert res.status_code == 200
    data = res.json()
    # Should include at least one entry for our product
    product_entries = [e for e in data if e["product_id"] == sample_product["id"]]
    assert len(product_entries) >= 1


def test_analytics_are_shop_scoped(app_client):
    """
    Cross-shop isolation: Shop A's sales must not appear in Shop B's analytics.

    Create shop A, make a sale, register shop B, verify B sees zero data.
    """
    # Shop A
    res_a = app_client.post(
        "/auth/register",
        json={
            "shop_name": "Shop A",
            "full_name": "Owner A",
            "email": "owner-a@test.com",
            "password": "test1234",
        },
    )
    token_a = res_a.json()["access_token"]

    # Register a product and make a sale in Shop A
    headers_a = {"Authorization": f"Bearer {token_a}"}
    prod = app_client.post(
        "/products/",
        json={
            "name": "A Product",
            "category": "Test",
            "type": "variant",
            "unit": "piece",
            "selling_price": 1000.0,
            "purchase_price": 700.0,
            "stock_qty": 10,
        },
        headers=headers_a,
    ).json()

    app_client.post(
        "/sales/",
        json={"items": [{"product_id": prod["id"], "quantity": 1}]},
        headers=headers_a,
    )

    # Shop B
    res_b = app_client.post(
        "/auth/register",
        json={
            "shop_name": "Shop B",
            "full_name": "Owner B",
            "email": "owner-b@test.com",
            "password": "test1234",
        },
    )
    token_b = res_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Shop B should see NO sales data
    trend_b = app_client.get("/analytics/revenue-trend", headers=headers_b)
    assert sum(e["revenue"] for e in trend_b.json()) == 0.0

    top_b = app_client.get("/analytics/top-products?period=month", headers=headers_b)
    assert top_b.json() == []

    margins_b = app_client.get("/analytics/profit-margins", headers=headers_b)
    assert margins_b.json() == []

    # Shop A should see its sale
    trend_a = app_client.get("/analytics/revenue-trend", headers=headers_a)
    assert sum(e["revenue"] for e in trend_a.json()) == 1000.0


# ─── Summary endpoint tests ──────────────────────────────────────


def test_summary_returns_all_sections(owner_client, sample_product):
    """Summary returns counts, top_products, profit_margins, peak_hours,
    expense_breakdown, recent_price_changes — all in one response."""
    owner_client.post(
        "/sales/",
        json={"items": [{"product_id": sample_product["id"], "quantity": 2}]},
    )
    owner_client.post("/expenses/", json={"name": "Tea", "amount": 300, "category": "Food"})

    res = owner_client.get("/analytics/summary?period=day")
    assert res.status_code == 200
    data = res.json()

    assert "counts" in data
    assert "top_products" in data
    assert "profit_margins" in data
    assert "peak_hours" in data
    assert "expense_breakdown" in data
    assert "recent_price_changes" in data
    assert "generated_at" in data
    assert data["period"] == "day"

    assert data["counts"]["total_products"] >= 1
    assert data["counts"]["total_sales"] >= 1
    assert len(data["top_products"]) >= 1
    assert len(data["profit_margins"]) >= 1
    assert len(data["peak_hours"]) == 24
    assert any(e["category"] == "Food" for e in data["expense_breakdown"])


def test_summary_respects_period(owner_client, sample_product):
    """period=day|week|month|unknown all return 200."""
    for p in ("day", "week", "month"):
        res = owner_client.get(f"/analytics/summary?period={p}")
        assert res.status_code == 200
        assert res.json()["period"] == p

    # Unknown period falls back to "day"
    res = owner_client.get("/analytics/summary?period=bogus")
    assert res.status_code == 200
    assert res.json()["period"] == "day"


def test_summary_includes_price_changes(owner_client):
    """Summary includes recent price changes without N+1."""
    res = owner_client.post(
        "/products/",
        json={
            "name": "Price Changer",
            "category": "Test",
            "type": "variant",
            "unit": "piece",
            "selling_price": 1000.0,
            "purchase_price": 700.0,
            "stock_qty": 10,
        },
    )
    product_id = res.json()["id"]

    owner_client.put(f"/products/{product_id}", json={"selling_price": 1500.0})

    summary_res = owner_client.get("/analytics/summary")
    data = summary_res.json()

    changes = data["recent_price_changes"]
    assert any(c["product"]["id"] == product_id for c in changes)


def test_summary_shop_scoped(owner_client, app_client, sample_product):
    """Another shop cannot see this shop's summary data."""
    owner_client.post(
        "/sales/",
        json={"items": [{"product_id": sample_product["id"], "quantity": 1}]},
    )

    app_client.post(
        "/auth/register",
        json={
            "shop_name": "Shop B",
            "full_name": "Owner B",
            "email": "owner-b-summary@test.com",
            "password": "test1234",
        },
    )
    token_b = app_client.post(
        "/auth/login",
        data={"username": "owner-b-summary@test.com", "password": "test1234"},
    ).json()["access_token"]

    res = app_client.get(
        "/analytics/summary",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    data = res.json()

    assert data["counts"]["total_products"] == 0
    assert data["counts"]["total_sales"] == 0
    assert data["top_products"] == []
    assert data["profit_margins"] == []
    assert data["recent_price_changes"] == []