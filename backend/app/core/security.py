"""
Password hashing + JWT token utilities.
Reads SECRET_KEY and ACCESS_TOKEN_EXPIRE_MINUTES from core.config (which
loads them from .env). Never hardcode secrets here.
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from jose import jwt

from app.core.config import ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, SECRET_KEY


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a stored PBKDF2 hash (salt$hash)."""
    try:
        salt, stored_hash = hashed_password.split("$", 1)
    except ValueError:
        return False
    new_hash = hashlib.pbkdf2_hmac("sha256", plain_password.encode(), salt.encode(), 100000)
    return secrets.compare_digest(new_hash.hex(), stored_hash)


def get_password_hash(password: str) -> str:
    """Generate a secure PBKDF2 hash: salt$hash."""
    salt = secrets.token_hex(16)
    hash_bytes = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
    return f"{salt}${hash_bytes.hex()}"


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Create a JWT. Defaults to ACCESS_TOKEN_EXPIRE_MINUTES (7 days) — not 15 min.
    Uses timezone-aware UTC datetime to avoid deprecation warning and TZ bugs.
    """
    to_encode = data.copy()
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT. Raises JWTError on failure."""
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
