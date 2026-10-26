"""Tests for sale creation, payment rules, void."""


def test_create_paid_sale_autosets_amount_paid(owner_client, sample_product):
    """A default sale should auto-set amount_paid = total_amount."""
    res = owner_client.post(
        "/sales/",
        json={
            "items": [{"product_id": sample_product["id"], "quantity": 2}],
            "payment_status": "paid",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_amount"] == 2000.0  # 2 × 1000
    # Re-fetch to see amount_paid (SaleResponse only returns id + total)


def test_create_sale_decrements_stock(owner_client, sample_product):
    owner_client.post(
        "/sales/",
        json={"items": [{"product_id": sample_product["id"], "quantity": 5}]},
    )
    res = owner_client.get("/products/")
    product = next(p for p in res.json() if p["id"] == sample_product["id"])
    assert product["stock_qty"] == 45  # 50 - 5


def test_create_sale_insufficient_stock(owner_client, sample_product):
    res = owner_client.post(
        "/sales/",
        json={"items": [{"product_id": sample_product["id"], "quantity": 9999}]},
    )
    assert res.status_code == 400
    assert "stock" in res.json()["detail"].lower()


def test_unpaid_sale_requires_customer(owner_client, sample_product):
    res = owner_client.post(
        "/sales/",
        json={
            "items": [{"product_id": sample_product["id"], "quantity": 1}],
            "payment_status": "unpaid",
        },
    )
    assert res.status_code == 400
    assert "customer" in res.json()["detail"].lower()


def test_unpaid_sale_increases_credit(owner_client, sample_product, sample_customer):
    res = owner_client.post(
        "/sales/",
        json={
            "items": [{"product_id": sample_product["id"], "quantity": 3}],
            "customer_id": sample_customer["id"],
            "payment_status": "unpaid",
        },
    )
    assert res.status_code == 200

    debtors_res = owner_client.get("/customers/debtors")
    debtor = next(d for d in debtors_res.json() if d["id"] == sample_customer["id"])
    assert debtor["total_credit"] == 3000.0  # 3 × 1000


def test_partial_sale_requires_amount_paid(owner_client, sample_product, sample_customer):
    res = owner_client.post(
        "/sales/",
        json={
            "items": [{"product_id": sample_product["id"], "quantity": 2}],
            "customer_id": sample_customer["id"],
            "payment_status": "partial",
            "amount_paid": 0,
        },
    )
    assert res.status_code == 400


def test_partial_sale_with_valid_amount(owner_client, sample_product, sample_customer):
    res = owner_client.post(
        "/sales/",
        json={
            "items": [{"product_id": sample_product["id"], "quantity": 2}],
            "customer_id": sample_customer["id"],
            "payment_status": "partial",
            "amount_paid": 500,
        },
    )
    assert res.status_code == 200

    debtors_res = owner_client.get("/customers/debtors")
    debtor = next(d for d in debtors_res.json() if d["id"] == sample_customer["id"])
    assert debtor["total_credit"] == 1500.0  # 2000 - 500


def test_void_sale_restores_stock(owner_client, sample_product):
    create_res = owner_client.post(
        "/sales/",
        json={"items": [{"product_id": sample_product["id"], "quantity": 3}]},
    )
    sale_id = create_res.json()["id"]

    void_res = owner_client.post(f"/sales/{sale_id}/void")
    assert void_res.status_code == 200

    products_res = owner_client.get("/products/")
    product = next(p for p in products_res.json() if p["id"] == sample_product["id"])
    assert product["stock_qty"] == 50  # back to original


def test_cannot_void_twice(owner_client, sample_product):
    create_res = owner_client.post(
        "/sales/",
        json={"items": [{"product_id": sample_product["id"], "quantity": 1}]},
    )
    sale_id = create_res.json()["id"]

    owner_client.post(f"/sales/{sale_id}/void")
    res2 = owner_client.post(f"/sales/{sale_id}/void")
    assert res2.status_code == 400


def test_cashier_cannot_void(cashier_client, sample_product):
    create_res = cashier_client.post(
        "/sales/",
        json={"items": [{"product_id": sample_product["id"], "quantity": 1}]},
    )
    sale_id = create_res.json()["id"]

    res = cashier_client.post(f"/sales/{sale_id}/void")
    assert res.status_code == 403

# ─── GET /sales/ richer response tests ──────────────────────────


def test_get_sales_returns_line_items(owner_client, sample_product, sample_customer):
    """GET /sales/ returns items with quantity + unit_price + total_price."""
    owner_client.post(
        "/sales/",
        json={
            "items": [{"product_id": sample_product["id"], "quantity": 2}],
            "customer_id": sample_customer["id"],
            "payment_status": "unpaid",
        },
    )
    res = owner_client.get("/sales/")
    assert res.status_code == 200
    body = res.json()
    # New response shape: { sales, total, has_more }
    assert "sales" in body
    assert body["total"] >= 1
    sale = body["sales"][0]
    assert "items" in sale
    assert len(sale["items"]) >= 1
    it = sale["items"][0]
    assert it["name"] == sample_product["name"]
    assert it["quantity"] == 2
    assert "unit_price" in it
    assert "total_price" in it
    # Backward-compat fields present
    assert sale["customer_name"] == sample_customer["name"]
    assert isinstance(sale["products"], list)


def test_get_sales_supports_pagination(owner_client, sample_product):
    """limit + offset page through results."""
    for i in range(3):
        owner_client.post(
            "/sales/",
            json={"items": [{"product_id": sample_product["id"], "quantity": 1}]},
        )
    r1 = owner_client.get("/sales/?limit=2&offset=0").json()
    assert len(r1["sales"]) == 2
    assert r1["has_more"] is True

    r2 = owner_client.get("/sales/?limit=2&offset=2").json()
    assert len(r2["sales"]) == 1
    assert r2["has_more"] is False


def test_get_sales_filter_by_voided_status(owner_client, sample_product):
    """?status=voided only returns voided sales."""
    sale = owner_client.post(
        "/sales/",
        json={"items": [{"product_id": sample_product["id"], "quantity": 1}]},
    ).json()
    sale_id = sale["id"]
    owner_client.post(f"/sales/{sale_id}/void")

    voided = owner_client.get("/sales/?status=voided").json()
    assert all(s["is_voided"] for s in voided["sales"])

    paid = owner_client.get("/sales/?status=paid").json()
    assert all(not s["is_voided"] for s in paid["sales"])