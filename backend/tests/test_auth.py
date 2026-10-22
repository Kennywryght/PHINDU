"""Tests for authentication: register, login, me, role enforcement."""


def test_register_creates_user(app_client):
    res = app_client.post(
        "/auth/register",
        json={
            "shop_name": "New Shop",
            "full_name": "Jane Doe",
            "email": "jane@example.com",
            "password": "secure123",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_register_rejects_duplicate_email(app_client):
    payload = {
        "shop_name": "Shop A",
        "full_name": "Alice",
        "email": "alice@example.com",
        "password": "secure123",
    }
    res1 = app_client.post("/auth/register", json=payload)
    assert res1.status_code == 201

    res2 = app_client.post("/auth/register", json=payload)
    assert res2.status_code == 400
    assert "already registered" in res2.json()["detail"].lower()


def test_register_rejects_short_password(app_client):
    res = app_client.post(
        "/auth/register",
        json={
            "shop_name": "Shop",
            "full_name": "Bob",
            "email": "bob@example.com",
            "password": "abc",  # < 6 chars
        },
    )
    assert res.status_code == 422


def test_register_rejects_invalid_email(app_client):
    res = app_client.post(
        "/auth/register",
        json={
            "shop_name": "Shop",
            "full_name": "Bob",
            "email": "not-an-email",
            "password": "secure123",
        },
    )
    assert res.status_code == 422


def test_login_success(owner_client):
    res = owner_client.post(
        "/auth/login",
        data={"username": "owner@test.com", "password": "test1234"},
    )
    assert res.status_code == 200
    assert "access_token" in res.json()


def test_login_wrong_password(app_client):
    app_client.post(
        "/auth/register",
        json={
            "shop_name": "S",
            "full_name": "U",
            "email": "u@test.com",
            "password": "correct-pass",
        },
    )
    res = app_client.post(
        "/auth/login",
        data={"username": "u@test.com", "password": "wrong-pass"},
    )
    assert res.status_code == 401


def test_me_returns_user(owner_client):
    res = owner_client.get("/auth/me")
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == "owner@test.com"
    assert data["role"] == "owner"
    assert data["is_active"] is True


def test_me_requires_token(app_client):
    res = app_client.get("/auth/me")
    assert res.status_code == 401


def test_me_rejects_bad_token(app_client):
    res = app_client.get(
        "/auth/me",
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert res.status_code == 401


def test_deactivated_user_cannot_login(owner_client):
    from app.db.models.user import User
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "owner@test.com").first()
        user.is_active = False
        db.commit()
    finally:
        db.close()

    res = owner_client.post(
        "/auth/login",
        data={"username": "owner@test.com", "password": "test1234"},
    )
    assert res.status_code == 403
    assert "deactivated" in res.json()["detail"].lower()


def test_deactivated_user_token_rejected(owner_client):
    """Even if the token is valid, a deactivated user should be blocked."""
    from app.db.models.user import User
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "owner@test.com").first()
        user.is_active = False
        db.commit()
    finally:
        db.close()

    res = owner_client.get("/auth/me")
    assert res.status_code == 403
