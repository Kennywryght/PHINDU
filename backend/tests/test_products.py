"""Tests for product CRUD, soft-delete, archive."""


def test_create_product(owner_client):
    res = owner_client.post(
        "/products/",
        json={
            "name": "Rice 5kg",
            "category": "Food",
            "type": "variant",
            "unit": "piece",
            "selling_price": 8000.0,
            "purchase_price": 6000.0,
            "stock_qty": 20,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "Rice 5kg"
    assert data["stock_qty"] == 20
    assert "id" in data


def test_create_product_creates_stock_batch(owner_client):
    res = owner_client.post(
        "/products/",
        json={
            "name": "Salt",
            "category": "Food",
            "type": "variant",
            "unit": "piece",
            "selling_price": 500.0,
            "purchase_price": 300.0,
            "stock_qty": 10,
        },
    )
    assert res.status_code == 200
    product_id = res.json()["id"]

    from app.db.models.stock import StockBatch
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        batch = db.query(StockBatch).filter(StockBatch.product_id == product_id).first()
        assert batch is not None
        assert batch.quantity_added == 10
        assert batch.shop_id is not None
    finally:
        db.close()


def test_list_products(owner_client, sample_product):
    res = owner_client.get("/products/")
    assert res.status_code == 200
    products = res.json()
    assert any(p["id"] == sample_product["id"] for p in products)


def test_update_product(owner_client, sample_product):
    res = owner_client.put(
        f"/products/{sample_product['id']}",
        json={"selling_price": 1500.0},
    )
    assert res.status_code == 200
    assert res.json()["selling_price"] == 1500.0


def test_update_stock_creates_batch(owner_client, sample_product):
    """Increasing stock should create a new StockBatch."""
    res = owner_client.put(
        f"/products/{sample_product['id']}",
        json={"stock_qty": 100},  # was 50
    )
    assert res.status_code == 200
    assert res.json()["stock_qty"] == 100

    from app.db.models.stock import StockBatch
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        batches = (
            db.query(StockBatch)
            .filter(StockBatch.product_id == sample_product["id"])
            .order_by(StockBatch.date_added.desc())
            .all()
        )
        assert len(batches) >= 2
        assert batches[0].quantity_added == 50  # increase of 50
    finally:
        db.close()


def test_delete_product_soft_when_used(owner_client, sample_product):
    """Product with sales gets soft-deleted, not hard-deleted."""
    # Create a sale first
    owner_client.post(
        "/sales/",
        json={
            "items": [{"product_id": sample_product["id"], "quantity": 1}],
        },
    )

    res = owner_client.delete(f"/products/{sample_product['id']}")
    assert res.status_code == 200
    assert "soft-deleted" in res.json()["message"].lower()

    # Still in DB but marked deleted
    res2 = owner_client.get("/products/?include_deleted=true")
    assert any(p["id"] == sample_product["id"] for p in res2.json())


def test_delete_product_hard_when_unused(owner_client):
    """Product with no sales gets hard-deleted."""
    res = owner_client.post(
        "/products/",
        json={
            "name": "Unused Product",
            "category": "Misc",
            "type": "variant",
            "unit": "piece",
            "selling_price": 100.0,
            "purchase_price": 50.0,
            "stock_qty": 1,
        },
    )
    product_id = res.json()["id"]

    del_res = owner_client.delete(f"/products/{product_id}")
    assert del_res.status_code == 200

    res2 = owner_client.get("/products/?include_deleted=true")
    assert not any(p["id"] == product_id for p in res2.json())


def test_archive_and_restore(owner_client, sample_product):
    res = owner_client.put(f"/products/archive/{sample_product['id']}")
    assert res.status_code == 200

    res2 = owner_client.put(f"/products/unarchive/{sample_product['id']}")
    assert res2.status_code == 200


def test_cashier_cannot_delete_product(cashier_client, sample_product):
    res = cashier_client.delete(f"/products/{sample_product['id']}")
    assert res.status_code == 403
    assert "owner" in res.json()["detail"].lower()
