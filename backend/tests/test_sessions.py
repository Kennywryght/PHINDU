"""Tests for session (daily shift) open/close and live summary math."""


def test_open_session_with_zero_balance(owner_client):
    res = owner_client.post("/sessions/open?opening_balance=0")
    assert res.status_code == 200
    data = res.json()
    assert data["opening_balance"] == 0
    assert data["is_active"] is True


def test_open_session_with_balance(owner_client):
    res = owner_client.post("/sessions/open?opening_balance=5000")
    assert res.status_code == 200
    assert res.json()["opening_balance"] == 5000


def test_cannot_open_two_sessions(owner_client):
    owner_client.post("/sessions/open?opening_balance=1000")
    res = owner_client.post("/sessions/open?opening_balance=2000")
    assert res.status_code == 400
    assert "already" in res.json()["detail"].lower()


def test_current_session_returns_active(owner_client):
    owner_client.post("/sessions/open?opening_balance=1000")
    res = owner_client.get("/sessions/current")
    assert res.status_code == 200
    assert res.json()["is_active"] is True


def test_summary_without_session_returns_404(app_client):
    """Fresh shop, no session — summary should 404."""
    app_client.post(
        "/auth/register",
        json={
            "shop_name": "S",
            "full_name": "U",
            "email": "summary-404@test.com",
            "password": "test1234",
        },
    )
    token = app_client.post(
        "/auth/login",
        data={"username": "summary-404@test.com", "password": "test1234"},
    ).json()["access_token"]
    app_client.headers["Authorization"] = f"Bearer {token}"

    res = app_client.get("/sessions/current/summary")
    assert res.status_code == 404


def test_summary_math_is_correct(owner_client, sample_product, sample_customer):
    """
    Open session with 5000 cash. Create:
      - 1 paid sale for 2000 (cash_sales)
      - 1 unpaid sale for 1000 (credit_sales)
      - 1 expense of 300

    expected_in_drawer = 5000 + 2000 - 300 = 6700
    """
    owner_client.post("/sessions/open?opening_balance=5000")

    # Paid sale
    owner_client.post(
        "/sales/",
        json={
            "items": [{"product_id": sample_product["id"], "quantity": 2}],
            "payment_status": "paid",
        },
    )

    # Unpaid sale
    owner_client.post(
        "/sales/",
        json={
            "items": [{"product_id": sample_product["id"], "quantity": 1}],
            "customer_id": sample_customer["id"],
            "payment_status": "unpaid",
        },
    )

    # Expense
    owner_client.post(
        "/expenses/",
        json={"name": "Tea", "amount": 300, "category": "Food"},
    )

    res = owner_client.get("/sessions/current/summary")
    assert res.status_code == 200
    data = res.json()

    assert data["sales"]["total_count"] == 2
    assert data["sales"]["cash_sales"] == 2000.0
    assert data["sales"]["credit_sales"] == 1000.0
    assert data["sales"]["total_sales"] == 3000.0

    assert data["expenses"]["count"] == 1
    assert data["expenses"]["total"] == 300.0

    assert data["cash_drawer"]["opening_balance"] == 5000.0
    assert data["cash_drawer"]["plus_cash_sales"] == 2000.0
    assert data["cash_drawer"]["minus_expenses"] == 300.0
    assert data["cash_drawer"]["expected_in_drawer"] == 6700.0


def test_close_session_computes_totals(owner_client, sample_product):
    owner_client.post("/sessions/open?opening_balance=1000")
    owner_client.post(
        "/sales/",
        json={"items": [{"product_id": sample_product["id"], "quantity": 1}]},
    )

    res = owner_client.post("/sessions/close?closing_balance=2000")
    assert res.status_code == 200
    session = res.json()["session"]
    assert session["is_active"] is False
    assert session["total_sales"] == 1000.0
    assert session["cash_sales"] == 1000.0
    assert session["credit_sales"] == 0.0


def test_voided_sales_excluded_from_close(owner_client, sample_product):
    owner_client.post("/sessions/open?opening_balance=0")

    # Paid sale
    sale = owner_client.post(
        "/sales/",
        json={"items": [{"product_id": sample_product["id"], "quantity": 2}]},
    ).json()

    # Void it
    owner_client.post(f"/sales/{sale['id']}/void")

    # Close session — total_sales should be 0 (voided excluded)
    res = owner_client.post("/sessions/close?closing_balance=0")
    assert res.status_code == 200
    assert res.json()["session"]["total_sales"] == 0.0


def test_cashier_cannot_close_session(cashier_client, owner_client):
    owner_client.post("/sessions/open?opening_balance=0")
    res = cashier_client.post("/sessions/close?closing_balance=100")
    assert res.status_code == 403
    assert "manager" in res.json()["detail"].lower() or "owner" in res.json()["detail"].lower()


def test_close_without_session_returns_404(app_client):
    app_client.post(
        "/auth/register",
        json={
            "shop_name": "S",
            "full_name": "U",
            "email": "close-404@test.com",
            "password": "test1234",
        },
    )
    token = app_client.post(
        "/auth/login",
        data={"username": "close-404@test.com", "password": "test1234"},
    ).json()["access_token"]
    app_client.headers["Authorization"] = f"Bearer {token}"

    res = app_client.post("/sessions/close?closing_balance=100")
    assert res.status_code == 404
