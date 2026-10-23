"""Tests for product CRUD, soft-delete, archive, variants."""


def _create_product(client, **overrides):
    """Helper to create a product."""
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


def _make_sale(client, product_id, quantity):
    """Helper to record a sale containing the given product (cash, fully paid)."""
    res = client.post(
        "/sales/",
        json={"items": [{"product_id": product_id, "quantity": quantity}]},
    )
    assert res.status_code in (200, 201), f"Sale creation failed: {res.text}"
    return res.json()


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
    assert data["parent_id"] is None
    assert data["is_parent"] is False
    assert data["variant_count"] == 0


def test_create_product_creates_stock_batch(owner_client):
    res = _create_product(owner_client, name="Salt", stock_qty=10)
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


def test_get_single_product(owner_client, sample_product):
    res = owner_client.get(f"/products/{sample_product['id']}")
    assert res.status_code == 200
    assert res.json()["id"] == sample_product["id"]
    assert "is_parent" in res.json()
    assert "variant_count" in res.json()


def test_update_product(owner_client, sample_product):
    res = owner_client.put(
        f"/products/{sample_product['id']}",
        json={"selling_price": 1500.0},
    )
    assert res.status_code == 200
    assert res.json()["selling_price"] == 1500.0


def test_update_stock_creates_batch(owner_client, sample_product):
    res = owner_client.put(
        f"/products/{sample_product['id']}",
        json={"stock_qty": 100},
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
        assert batches[0].quantity_added == 50
    finally:
        db.close()


def test_delete_product_soft_when_used(owner_client, sample_product):
    owner_client.post(
        "/sales/",
        json={"items": [{"product_id": sample_product["id"], "quantity": 1}]},
    )

    res = owner_client.delete(f"/products/{sample_product['id']}")
    assert res.status_code == 200
    assert "soft-deleted" in res.json()["message"].lower()

    res2 = owner_client.get("/products/?include_deleted=true")
    assert any(p["id"] == sample_product["id"] for p in res2.json())


def test_delete_product_hard_when_unused(owner_client):
    res = _create_product(owner_client, name="Unused Product", stock_qty=1)
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


# ─── VARIANT TESTS ────────────────────────────────────────────────


def test_create_parent_product(owner_client):
    """A parent product has no price/stock but can hold variants."""
    res = _create_product(
        owner_client,
        name="Sugar",
        selling_price=0,
        purchase_price=0,
        stock_qty=0,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "Sugar"
    assert data["selling_price"] == 0
    assert data["stock_qty"] == 0
    assert data["parent_id"] is None


def test_create_variant_under_parent(owner_client):
    """Create parent then a variant."""
    parent_res = _create_product(
        owner_client,
        name="Sugar",
        selling_price=0,
        purchase_price=0,
        stock_qty=0,
    )
    parent_id = parent_res.json()["id"]

    variant_res = _create_product(
        owner_client,
        name="Sugar 1kg",
        selling_price=1500,
        purchase_price=1000,
        stock_qty=50,
        parent_id=parent_id,
    )
    assert variant_res.status_code == 200
    data = variant_res.json()
    assert data["parent_id"] == parent_id
    assert data["is_parent"] is False


def test_parent_has_variant_count(owner_client):
    """After adding variants, parent reports variant_count > 0."""
    parent_res = _create_product(
        owner_client,
        name="Sugar",
        selling_price=0,
        purchase_price=0,
        stock_qty=0,
    )
    parent_id = parent_res.json()["id"]

    _create_product(owner_client, name="Sugar 1kg", parent_id=parent_id)
    _create_product(owner_client, name="Sugar 2kg", parent_id=parent_id)

    res = owner_client.get(f"/products/{parent_id}")
    data = res.json()
    assert data["variant_count"] == 2
    assert data["is_parent"] is True


def test_get_parents_only(owner_client):
    """parents_only=true filters out variants."""
    parent_res = _create_product(
        owner_client, name="Parent", selling_price=0, purchase_price=0, stock_qty=0
    )
    parent_id = parent_res.json()["id"]
    _create_product(owner_client, name="Variant 1", parent_id=parent_id)

    res = owner_client.get("/products/?parents_only=true")
    assert res.status_code == 200
    products = res.json()
    assert any(p["id"] == parent_id for p in products)
    assert all(p["parent_id"] is None for p in products)


def test_get_variants_of_parent(owner_client):
    """GET /products/{parent_id}/variants returns only children."""
    parent_res = _create_product(
        owner_client, name="Parent", selling_price=0, purchase_price=0, stock_qty=0
    )
    parent_id = parent_res.json()["id"]

    v1 = _create_product(owner_client, name="Var 1", parent_id=parent_id, stock_qty=5)
    v2 = _create_product(owner_client, name="Var 2", parent_id=parent_id, stock_qty=10)

    res = owner_client.get(f"/products/{parent_id}/variants")
    assert res.status_code == 200
    variants = res.json()
    assert len(variants) == 2
    variant_ids = {v["id"] for v in variants}
    assert v1.json()["id"] in variant_ids
    assert v2.json()["id"] in variant_ids
    assert "selling_price" in variants[0]
    assert "stock_qty" in variants[0]


def test_cannot_create_variant_of_variant(owner_client):
    """Nested variants are rejected."""
    parent_res = _create_product(
        owner_client, name="Parent", selling_price=0, purchase_price=0, stock_qty=0
    )
    parent_id = parent_res.json()["id"]

    v1 = _create_product(owner_client, name="V1", parent_id=parent_id)
    v1_id = v1.json()["id"]

    res = _create_product(owner_client, name="V1 Sub", parent_id=v1_id)
    assert res.status_code == 400
    assert "nest" in res.json()["detail"].lower() or "top-level" in res.json()["detail"].lower()


def test_cannot_create_variant_with_invalid_parent(owner_client):
    """Parent_id that doesn't exist returns 404."""
    res = _create_product(
        owner_client,
        name="Orphan",
        parent_id="nonexistent-id-12345",
    )
    assert res.status_code == 404


def test_cannot_delete_parent_with_variants(owner_client):
    """Deleting a parent with variants is blocked."""
    parent_res = _create_product(
        owner_client, name="Parent", selling_price=0, purchase_price=0, stock_qty=0
    )
    parent_id = parent_res.json()["id"]
    _create_product(owner_client, name="V1", parent_id=parent_id)

    res = owner_client.delete(f"/products/{parent_id}")
    assert res.status_code == 400
    assert "variant" in res.json()["detail"].lower()


# ─── PRICE HISTORY TESTS ──────────────────────────────────────────


def test_price_history_seeded_on_create(owner_client):
    res = _create_product(
        owner_client,
        name="Sugar",
        selling_price=1500,
        purchase_price=1000,
    )
    product_id = res.json()["id"]

    history_res = owner_client.get(f"/products/{product_id}/price-history")
    assert history_res.status_code == 200
    data = history_res.json()
    types = {h["price_type"] for h in data["history"]}
    assert types == {"selling", "purchase"}


def test_price_history_selling_change(owner_client):
    res = _create_product(owner_client, name="A", selling_price=1000, purchase_price=700)
    product_id = res.json()["id"]

    owner_client.put(f"/products/{product_id}", json={"selling_price": 1500})

    history_res = owner_client.get(f"/products/{product_id}/price-history")
    data = history_res.json()
    selling_changes = [
        h for h in data["history"]
        if h["price_type"] == "selling" and h["old_price"] == 1000 and h["new_price"] == 1500
    ]
    assert len(selling_changes) == 1
    assert selling_changes[0]["change_percent"] == 50.0


def test_price_history_purchase_change(owner_client):
    res = _create_product(owner_client, name="B", selling_price=1000, purchase_price=700)
    product_id = res.json()["id"]

    owner_client.put(f"/products/{product_id}", json={"purchase_price": 900})

    history_res = owner_client.get(f"/products/{product_id}/price-history")
    data = history_res.json()
    purchase_changes = [
        h for h in data["history"]
        if h["price_type"] == "purchase" and h["old_price"] == 700 and h["new_price"] == 900
    ]
    assert len(purchase_changes) == 1


def test_price_history_no_change_no_log(owner_client):
    res = _create_product(owner_client, name="C", selling_price=1000, purchase_price=700)
    product_id = res.json()["id"]

    before = len(owner_client.get(f"/products/{product_id}/price-history").json()["history"])

    owner_client.put(f"/products/{product_id}", json={"selling_price": 1000})

    after = len(owner_client.get(f"/products/{product_id}/price-history").json()["history"])
    assert after == before


def test_price_history_returns_current_margin(owner_client):
    res = _create_product(owner_client, name="D", selling_price=1500, purchase_price=1000)
    product_id = res.json()["id"]

    data = owner_client.get(f"/products/{product_id}/price-history").json()
    product = data["product"]
    assert product["current_selling_price"] == 1500
    assert product["current_purchase_price"] == 1000
    assert product["current_margin_percent"] == 33.33


def test_price_history_shop_scoped(owner_client, app_client):
    res = _create_product(owner_client, name="E", selling_price=1000, purchase_price=700)
    product_id = res.json()["id"]

    app_client.post(
        "/auth/register",
        json={
            "shop_name": "Shop B",
            "full_name": "Owner B",
            "email": "owner-b@test.com",
            "password": "test1234",
        },
    )
    token_b = app_client.post(
        "/auth/login",
        data={"username": "owner-b@test.com", "password": "test1234"},
    ).json()["access_token"]

    res = app_client.get(
        f"/products/{product_id}/price-history",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res.status_code == 404


# ─── RESTOCK TESTS ────────────────────────────────────────────────


def test_restock_adds_stock_and_batch(owner_client, sample_product):
    initial_stock = sample_product["stock_qty"]

    res = owner_client.post(
        f"/products/{sample_product['id']}/restock",
        json={"quantity": 25, "cost_per_unit": 800, "notes": "Restock from ABC"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["product"]["stock_qty"] == initial_stock + 25
    assert data["batch"]["quantity_added"] == 25
    assert data["batch"]["cost_per_unit"] == 800


def test_restock_validates_quantity(owner_client, sample_product):
    res = owner_client.post(
        f"/products/{sample_product['id']}/restock",
        json={"quantity": 0},
    )
    assert res.status_code in (400, 422)


def test_restock_creates_new_batch(owner_client, sample_product):
    from app.db.models.stock import StockBatch
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        count_before = db.query(StockBatch).filter(
            StockBatch.product_id == sample_product["id"]
        ).count()
    finally:
        db.close()

    owner_client.post(
        f"/products/{sample_product['id']}/restock",
        json={"quantity": 10},
    )

    db = SessionLocal()
    try:
        count_after = db.query(StockBatch).filter(
            StockBatch.product_id == sample_product["id"]
        ).count()
        assert count_after == count_before + 1
    finally:
        db.close()


def test_restock_history_endpoint(owner_client, sample_product):
    owner_client.post(
        f"/products/{sample_product['id']}/restock",
        json={"quantity": 20, "cost_per_unit": 750},
    )

    res = owner_client.get(f"/products/{sample_product['id']}/restocks")
    assert res.status_code == 200
    data = res.json()
    assert "product" in data
    assert "summary" in data
    assert "batches" in data
    assert data["summary"]["total_restocks"] >= 1
    assert data["summary"]["total_quantity_restocked"] >= 50 + 20


def test_restock_history_shop_scoped(owner_client, app_client, sample_product):
    app_client.post(
        "/auth/register",
        json={
            "shop_name": "Shop B",
            "full_name": "Owner B",
            "email": "owner-b@test.com",
            "password": "test1234",
        },
    )
    token_b = app_client.post(
        "/auth/login",
        data={"username": "owner-b@test.com", "password": "test1234"},
    ).json()["access_token"]

    res = app_client.get(
        f"/products/{sample_product['id']}/restocks",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res.status_code == 404


def test_cannot_restock_soft_deleted_product(owner_client):
    """Restock on a SOFT-deleted product (has sales) returns 400."""
    res = _create_product(owner_client, name="ToDelete", stock_qty=10)
    product_id = res.json()["id"]

    owner_client.post(
        "/sales/",
        json={"items": [{"product_id": product_id, "quantity": 1}]},
    )

    owner_client.delete(f"/products/{product_id}")

    restock_res = owner_client.post(
        f"/products/{product_id}/restock",
        json={"quantity": 10},
    )
    assert restock_res.status_code == 400
    assert "deleted" in restock_res.json()["detail"].lower()


def test_cannot_restock_hard_deleted_product(owner_client):
    """Restock on a HARD-deleted product (no sales) returns 404."""
    res = _create_product(owner_client, name="ToDeleteHard", stock_qty=10)
    product_id = res.json()["id"]

    owner_client.delete(f"/products/{product_id}")

    restock_res = owner_client.post(
        f"/products/{product_id}/restock",
        json={"quantity": 10},
    )
    assert restock_res.status_code == 404


def test_cannot_restock_parent_with_variants(owner_client):
    """Parent products with variants can't be restocked."""
    parent_res = _create_product(
        owner_client, name="Parent", selling_price=0, purchase_price=0, stock_qty=0
    )
    parent_id = parent_res.json()["id"]
    _create_product(owner_client, name="V1", parent_id=parent_id)

    res = owner_client.post(
        f"/products/{parent_id}/restock",
        json={"quantity": 10},
    )
    assert res.status_code == 400
    assert "variant" in res.json()["detail"].lower() or "parent" in res.json()["detail"].lower()


def test_sell_speed_endpoint(owner_client, sample_product):
    res = owner_client.get(f"/products/{sample_product['id']}/sell-speed")
    assert res.status_code == 200
    data = res.json()
    assert "product_id" in data
    assert "batches_analyzed" in data
    assert data["batches_analyzed"] == 0
    assert data["avg_days_to_sell"] is None


# ─── RESTOCK PREDICTION TESTS ─────────────────────────────────────


def test_restock_prediction_no_data(owner_client):
    """New product with no sales → method 'no_data'."""
    res = _create_product(owner_client, name="New Item", stock_qty=10)
    product_id = res.json()["id"]

    pred = owner_client.get(f"/products/{product_id}/restock-prediction")
    assert pred.status_code == 200
    data = pred.json()
    assert data["method"] == "no_data"
    assert data["days_until_restock"] is None


def test_restock_prediction_sales_velocity(owner_client):
    """Product with 1 batch, sells steadily → method 'sales_velocity'."""
    res = _create_product(owner_client, name="Steady", stock_qty=30)
    product_id = res.json()["id"]

    # Sell 10 units → avg 0.33/day, stock 20 → ~60 days
    _make_sale(owner_client, product_id, 10)

    pred = owner_client.get(f"/products/{product_id}/restock-prediction")
    data = pred.json()
    assert data["method"] == "sales_velocity"
    assert data["days_until_restock"] is not None


def test_restock_prediction_shop_scoped(owner_client, app_client):
    """Shop B cannot see Shop A's product prediction."""
    res = _create_product(owner_client, name="Secret", stock_qty=10)
    product_id = res.json()["id"]

    app_client.post(
        "/auth/register",
        json={
            "shop_name": "Shop B",
            "full_name": "Owner B",
            "email": "owner-b-pred@test.com",
            "password": "test1234",
        },
    )
    token_b = app_client.post(
        "/auth/login",
        data={"username": "owner-b-pred@test.com", "password": "test1234"},
    ).json()["access_token"]

    res = app_client.get(
        f"/products/{product_id}/restock-prediction",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res.status_code == 404


def test_restock_prediction_returns_structure(owner_client):
    """Prediction response has all expected fields."""
    res = _create_product(owner_client, name="Structure Check", stock_qty=10)
    sample_product = res.json()

    pred = owner_client.get(f"/products/{sample_product['id']}/restock-prediction")
    assert pred.status_code == 200
    data = pred.json()

    assert "product_id" in data
    assert "name" in data
    assert "current_stock" in data
    assert "days_until_restock" in data
    assert "confidence" in data
    assert "method" in data