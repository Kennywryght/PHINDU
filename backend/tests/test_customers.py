"""Tests for customer CRUD, credit flow, and payment audit trail."""


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
    """Payment should create a Payment row with method, session_id, etc."""
    # Open session so payment gets linked
    owner_client.post("/sessions/open?opening_balance=1000")

    # Create a debt
    owner_client.post(
        "/sales/",
        json={
            "items": [{"product_id": sample_product["id"], "quantity": 3}],
            "customer_id": sample_customer["id"],
            "payment_status": "unpaid",
        },
    )

    # Record partial payment
    res = owner_client.post(
        f"/customers/{sample_customer['id']}/record-payment",
        json={"amount": 1500, "method": "cash", "note": "partial"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["amount"] == 1500.0
    assert data["method"] == "cash"
    assert data["customer_id"] == sample_customer["id"]
    assert data["session_id"] is not None  # linked to active session
    assert data["sale_id"] is None


def test_record_payment_reduces_credit(owner_client, sample_product, sample_customer):
    owner_client.post(
        "/sales/",
        json={
            "items": [{"product_id": sample_product["id"], "quantity": 2}],
            "customer_id": sample_customer["id"],
            "payment_status": "unpaid",
        },
    )  # 2000 debt

    owner_client.post(
        f"/customers/{sample_customer['id']}/record-payment",
        json={"amount": 800, "method": "cash"},
    )

    res = owner_client.get("/customers/debtors")
    debtor = next(d for d in res.json() if d["id"] == sample_customer["id"])
    assert debtor["total_credit"] == 1200.0


def test_record_payment_cannot_go_negative(owner_client, sample_product, sample_customer):
    """Paying more than owed caps at 0 (no negative credit)."""
    owner_client.post(
        "/sales/",
        json={
            "items": [{"product_id": sample_product["id"], "quantity": 1}],
            "customer_id": sample_customer["id"],
            "payment_status": "unpaid",
        },
    )  # 1000 debt

    owner_client.post(
        f"/customers/{sample_customer['id']}/record-payment",
        json={"amount": 9999, "method": "cash"},
    )

    res = owner_client.get("/customers/debtors")
    assert res.json() == []  # no longer a debtor


def test_payment_against_specific_sale(owner_client, sample_product, sample_customer):
    """Paying off a specific sale updates that sale's amount_paid and status."""
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

    # Verify sale is now paid
    sales_res = owner_client.get("/sales/")
    updated = next(s for s in sales_res.json() if s["id"] == sale_id)
    assert updated["payment_status"] == "paid"
    assert updated["amount_paid"] == 2000.0


def test_payment_requires_matching_customer(owner_client, sample_product, sample_customer):
    """Cannot apply a payment to another customer's sale."""
    # Create a second customer
    c2 = owner_client.post("/customers/", json={"name": "Other Customer"}).json()

    # Create a sale for customer 1
    sale = owner_client.post(
        "/sales/",
        json={
            "items": [{"product_id": sample_product["id"], "quantity": 1}],
            "customer_id": sample_customer["id"],
            "payment_status": "unpaid",
        },
    ).json()

    # Try to pay from customer 2 against customer 1's sale
    res = owner_client.post(
        f"/customers/{c2['id']}/record-payment",
        json={"amount": 500, "method": "cash", "sale_id": sale["id"]},
    )
    assert res.status_code == 400
    assert "belong" in res.json()["detail"].lower()


def test_payment_history_endpoint(owner_client, sample_product, sample_customer):
    """GET /customers/{id}/payments returns audit trail."""
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
    assert res.status_code == 422  # Pydantic gt=0
