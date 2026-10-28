"""PHINDU API entry point."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

# Import ALL models so Base.metadata.create_all() sees every table
import app.db.models  # noqa: F401
from app.api.routes import (
    alerts,
    analytics,
    auth,
    customers,
    dashboard,
    expenses,
    products,
    sales,
    sessions,
)
from app.db.session import Base, engine

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# ── Rate limiter ──
# Per-IP rate limiting. Routes opt in via @limiter.limit(...).
# memory:// is fine for a single Render worker. If WEB_CONCURRENCY > 1,
# switch RATE_LIMIT_STORAGE to a redis:// URL.
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    storage_uri=os.getenv("RATE_LIMIT_STORAGE", "memory://"),
)

app = FastAPI(
    title="PHINDU API",
    swagger_ui_init_oauth={
        "clientId": "swagger-ui",
        "clientSecret": "",
        "appName": "PHINDU API",
        "usePkceWithAuthorizationCodeGrant": False,
    },
)

# Attach limiter to app (must happen before middleware registration)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# ── CORS ──
# Locked down. Only the real frontend (from env var) plus local dev
# origins can reach this API. No wildcard Vercel regex.
_env = os.getenv("ENV", "dev").lower()
_prod_origins = [
    u.strip() for u in os.getenv("FRONTEND_URLS", "").split(",") if u.strip()
]
_dev_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
]
_allowed = _prod_origins if _env == "prod" else _prod_origins + _dev_origins

if _env == "prod" and not _prod_origins:
    print("⚠️  ENV=prod but FRONTEND_URLS is empty — CORS will reject all browsers.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    max_age=600,
)

# Include routers
app.include_router(dashboard.router)
app.include_router(analytics.router)
app.include_router(products)
app.include_router(sales)
app.include_router(expenses.router)
app.include_router(alerts.router)
app.include_router(sessions.router)
app.include_router(customers.router)
app.include_router(auth.router)

# Create tables — safe because this is idempotent (only creates missing tables)
Base.metadata.create_all(bind=engine)


@app.get("/")
def root():
    return {"message": "PHINDU BACKEND RUNNING small businesses sales & insights 🔥"}


@app.get("/ping")
def ping():
    return {"ping": "pong"}