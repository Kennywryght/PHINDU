"""
Central configuration loader.

This module is imported EARLY (from main.py, session.py, security.py) so that
load_dotenv() runs before any other module reads os.getenv(...). This fixes
the previous bug where DATABASE_URL from .env was silently ignored.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Path to backend/.env — resolved from this file's location so it works
# no matter what directory uvicorn is started from.
_env_path = Path(__file__).resolve().parents[2] / ".env"
if _env_path.exists():
    load_dotenv(_env_path, override=False)  # do not override existing env vars


# ─── Database ────────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./phindu.db")

# ─── Auth ────────────────────────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY is not set. Add it to backend/.env:\n"
        "  SECRET_KEY=<64-char random hex>\n"
        "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
    )

ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080")  # default 7 days
)