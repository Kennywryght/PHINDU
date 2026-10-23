"""Tests for customer CRUD, credit flow, and payment audit trail + risk scoring."""


def test_create_customer(owner_client):
    res = owner_client.post(
        "/customers/",
        json={"name": "Alice Banda", "phone": "0999111111"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "Alice Banda"
    assert data["total_credit"] == 0.0
    assert "id" in data


def test_list_customers(owner_client, sample_customer):
    res = owner_client.get("/customers/")
    assert res.status_code == 200
    assert any(c["id"] == sample_customer["id"] for c in res.json())


def test_debtors_empty_when_no_credit(owner_client, sample_customer):
    res = owner_client.get("/customers/debtors")
    assert res.status_code == 200
    assert res.json() == []


def test_debtors_shows_after_unpaid_sale(owner_client, sample_product, sample_customer):
    owner_client.post(
        "/sales/",
        json={
            "items": [{"product_id": sample_product["id"], "quantity": 2}],
            "customer_id": sample_customer["id"],
            "payment_status": "unpaid",
        },
    )
    res = owner_client.get("/customers/debtors")
    assert res.status_code == 200
    debtors = res.json()
    assert len(debtors) == 1
    assert debtors[0]["id"] == sample_customer["id"]
    assert debtors[0]["total_credit"] == 2000.0


def test_record_payment_creates_audit_row(owner_client, sample_product, sample_customer):
    owner_client.post("/sessions/open?opening_balance=1000")
    owner_client.post(
        "/sales/",
        json={
            "items": [{"product_id": sample_product["id"], "quantity": 3}],
            "customer_id": sample_customer["id"],
            "payment_status": "unpaid",
        },
    )

    res = owner_client.post(
        f"/customers/{sample_customer['id']}/record-payment",
        json={"amount": 1500, "method": "cash", "note": "partial"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["amount"] == 1500.0
    assert data["method"] == "cash"
    assert data["customer_id"] == sample_customer["id"]
    assert data["session_id"] is not None
    assert data["sale_id"] is None


def test_record_payment_reduces_credit(owner_client, sample_product, sample_customer):
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
        json={"amount": 800, "method": "cash"},
    )
    res = owner_client.get("/customers/debtors")
    debtor = next(d for d in res.json() if d["id"] == sample_customer["id"])
    assert debtor["total_credit"] == 1200.0


def test_record_payment_cannot_go_negative(owner_client, sample_product, sample_customer):
    owner_client.post(
        "/sales/",
        json={
            "items": [{"product_id": sample_product["id"], "quantity": 1}],
            "customer_id": sample_customer["id"],
            "payment_status": "unpaid",
        },
    )
    owner_client.post(
        f"/customers/{sample_customer['id']}/record-payment",
        json={"amount": 9999, "method": "cash"},
    )
    res = owner_client.get("/customers/debtors")
    assert res.json() == []


def test_payment_against_specific_sale(owner_client, sample_product, sample_customer):
    sale = owner_client.post(
        "/sales/",
        json={
            "items": [{"product_id": sample_product["id"], "quantity": 2}],
            "customer_id": sample_customer["id"],
            "payment_status": "unpaid",
            "amount_paid": 0,
        },
    ).json()
    sale_id = sale["id"]

    owner_client.post(
        f"/customers/{sample_customer['id']}/record-payment",
        json={"amount": 2000, "method": "cash", "sale_id": sale_id},
    )

    sales_res = owner_client.get("/sales/")
    updated = next(s for s in sales_res.json() if s["id"] == sale_id)
    assert updated["payment_status"] == "paid"
    assert updated["amount_paid"] == 2000.0


def test_payment_requires_matching_customer(owner_client, sample_product, sample_customer):
    c2 = owner_client.post("/customers/", json={"name": "Other Customer"}).json()

    sale = owner_client.post(
        "/sales/",
        json={
            "items": [{"product_id": sample_product["id"], "quantity": 1}],
            "customer_id": sample_customer["id"],
            "payment_status": "unpaid",
        },
    ).json()

    res = owner_client.post(
        f"/customers/{c2['id']}/record-payment",
        json={"amount": 500, "method": "cash", "sale_id": sale["id"]},
    )
    assert res.status_code == 400
    assert "belong" in res.json()["detail"].lower()


def test_payment_history_endpoint(owner_client, sample_product, sample_customer):
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
        json={"amount": 500, "method": "cash"},
    )
    owner_client.post(
        f"/customers/{sample_customer['id']}/record-payment",
        json={"amount": 300, "method": "airtel_money"},
    )

    res = owner_client.get(f"/customers/{sample_customer['id']}/payments")
    assert res.status_code == 200
    payments = res.json()
    assert len(payments) == 2
    methods = {p["method"] for p in payments}
    assert methods == {"cash", "airtel_money"}


def test_cashier_cannot_record_payment(cashier_client, sample_product, sample_customer):
    cashier_client.post(
        "/sales/",
        json={
            "items": [{"product_id": sample_product["id"], "quantity": 1}],
            "customer_id": sample_customer["id"],
            "payment_status": "unpaid",
        },
    )
    res = cashier_client.post(
        f"/customers/{sample_customer['id']}/record-payment",
        json={"amount": 500, "method": "cash"},
    )
    assert res.status_code == 403


def test_payment_amount_must_be_positive(owner_client, sample_customer):
    res = owner_client.post(
        f"/customers/{sample_customer['id']}/record-payment",
        json={"amount": 0, "method": "cash"},
    )
    assert res.status_code == 422


# ─── CREDIT RISK SCORE TESTS ──────────────────────────────────────


def test_credit_risk_new_customer(owner_client):
    """Customer with no purchases → 'new' level, perfect score (no deductions)."""
    res = owner_client.post(
        "/customers/",
        json={"name": "New Customer", "phone": "0999"},
    )
    customer_id = res.json()["id"]

    risk_res = owner_client.get(f"/customers/{customer_id}/credit-risk")
    assert risk_res.status_code == 200
    risk = risk_res.json()

    assert risk["level"] == "new"
    assert risk["label"] == "New Customer"
    assert risk["score"] == 100  # no deductions for zero balance, no sales


def test_credit_risk_never_paid(owner_client, sample_product):
    """Customer with debt and no payments → high risk, big score hit."""
    cust = owner_client.post("/customers/", json={"name": "Bad Debtor"}).json()
    cust_id = cust["id"]

    owner_client.post(
        "/sales/",
        json={
            "items": [{"product_id": sample_product["id"], "quantity": 5}],
            "customer_id": cust_id,
            "payment_status": "unpaid",
        },
    )

    risk_res = owner_client.get(f"/customers/{cust_id}/credit-risk")
    risk = risk_res.json()

    assert risk["level"] in ("medium", "high")
    assert risk["score"] < 100
    assert any("never" in w.lower() or "no payment" in w.lower() for w in risk["warnings"])


def test_credit_risk_good_payer(owner_client, sample_product):
    """Customer who paid multiple times → higher score."""
    cust = owner_client.post("/customers/", json={"name": "Good Payer"}).json()
    cust_id = cust["id"]

    owner_client.post(
        "/sales/",
        json={
            "items": [{"product_id": sample_product["id"], "quantity": 2}],
            "customer_id": cust_id,
            "payment_status": "unpaid",
        },
    )

    owner_client.post(
        f"/customers/{cust_id}/record-payment",
        json={"amount": 500, "method": "cash"},
    )
    owner_client.post(
        f"/customers/{cust_id}/record-payment",
        json={"amount": 500, "method": "cash"},
    )
    owner_client.post(
        f"/customers/{cust_id}/record-payment",
        json={"amount": 1000, "method": "cash"},
    )

    risk_res = owner_client.get(f"/customers/{cust_id}/credit-risk")
    risk = risk_res.json()

    assert risk["level"] in ("low", "medium")
    assert risk["factors"]["payment_count"] == 3
    assert risk["factors"]["current_balance"] == 0


def test_debtors_with_risk_flag(owner_client, sample_product):
    """GET /customers/debtors?include_risk=true adds risk block per debtor."""
    cust = owner_client.post("/customers/", json={"name": "Debtor A"}).json()

    owner_client.post(
        "/sales/",
        json={
            "items": [{"product_id": sample_product["id"], "quantity": 2}],
            "customer_id": cust["id"],
            "payment_status": "unpaid",
        },
    )

    res = owner_client.get("/customers/debtors?include_risk=true")
    assert res.status_code == 200
    debtors = res.json()

    assert len(debtors) >= 1
    debtor = next(d for d in debtors if d["id"] == cust["id"])
    assert "risk" in debtor
    assert "score" in debtor["risk"]
    assert "level" in debtor["risk"]
    assert "recommendation" in debtor["risk"]


def test_debtors_without_risk_flag(owner_client, sample_product, sample_customer):
    """Default (no flag) → no risk block (backward compat)."""
    # NOTE: `sample_product` must be in the signature — it was the cause of the NameError.
    owner_client.post(
        "/sales/",
        json={
            "items": [{"product_id": sample_product["id"], "quantity": 1}],
            "customer_id": sample_customer["id"],
            "payment_status": "unpaid",
        },
    )
    res = owner_client.get("/customers/debtors")
    debtor = next((d for d in res.json() if d["id"] == sample_customer["id"]), None)
    assert debtor is not None
    assert "risk" not in debtor


def test_credit_risk_shop_scoped(owner_client, app_client):
    """Shop B cannot fetch Shop A customer's risk."""
    res = owner_client.post("/customers/", json={"name": "Shop A Customer"})
    cust_id = res.json()["id"]

    app_client.post(
        "/auth/register",
        json={
            "shop_name": "Shop B",
            "full_name": "Owner B",
            "email": "owner-b-risk@test.com",
            "password": "test1234",
        },
    )
    token_b = app_client.post(
        "/auth/login",
        data={"username": "owner-b-risk@test.com", "password": "test1234"},
    ).json()["access_token"]

    res = app_client.get(
        f"/customers/{cust_id}/credit-risk",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res.status_code == 404