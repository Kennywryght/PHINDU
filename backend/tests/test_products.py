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
    # Should have parent but no variants
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
    # VariantSummary has just the essential fields
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

    # Try to create a variant of a variant
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