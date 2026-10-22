"""PHINDU API entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer

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

app = FastAPI(
    title="PHINDU API",
    swagger_ui_init_oauth={
        "clientId": "swagger-ui",
        "clientSecret": "",
        "appName": "PHINDU API",
        "usePkceWithAuthorizationCodeGrant": False,
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://phindu-sb.vercel.app",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
