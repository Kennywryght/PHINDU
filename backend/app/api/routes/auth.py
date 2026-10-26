"""
Authentication routes: register, login, me, update, change-password.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.db.models.shop import Shop
from app.db.models.user import User
from app.db.session import get_db

router = APIRouter(prefix="/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ─── Schemas ─────────────────────────────────────────────────────
class Token(BaseModel):
    access_token: str
    token_type: str


class UserOut(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    shop_id: str
    shop_name: str | None = None
    is_active: bool


class RegisterRequest(BaseModel):
    shop_name: str = Field(..., min_length=1, max_length=100)
    full_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=72)


class UpdateProfileRequest(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=100)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6, max_length=72)


# ─── Dependency: current user from JWT ──────────────────────────
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exc
    except JWTError:
        raise credentials_exc

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise credentials_exc

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    return user


def _user_to_out(user: User, db: Session) -> dict:
    """Serialize a User, including the shop name for the profile page."""
    shop = db.query(Shop).filter(Shop.id == user.shop_id).first()
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "shop_id": user.shop_id,
        "shop_name": shop.name if shop else None,
        "is_active": bool(user.is_active),
    }


# ─── Endpoints ──────────────────────────────────────────────────
@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    if len(data.password.encode("utf-8")) > 72:
        raise HTTPException(status_code=400, detail="Password too long (max 72 bytes)")

    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    shop = Shop(id=str(uuid.uuid4()), name=data.shop_name.strip())
    db.add(shop)
    db.flush()

    user = User(
        id=str(uuid.uuid4()),
        shop_id=shop.id,
        email=data.email,
        hashed_password=get_password_hash(data.password),
        full_name=data.full_name.strip(),
        role="owner",
        is_active=True,
    )
    db.add(user)
    db.commit()

    token = create_access_token({"sub": user.id})
    return {"access_token": token, "token_type": "bearer"}


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    token = create_access_token({"sub": user.id})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserOut)
def get_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _user_to_out(current_user, db)


@router.put("/me", response_model=UserOut)
def update_me(
    data: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update the current user's profile. Only `full_name` is editable."""
    current_user.full_name = data.full_name.strip()
    db.commit()
    db.refresh(current_user)
    return _user_to_out(current_user, db)


@router.post("/change-password")
def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change the current user's password. Verifies current password first."""
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    if data.current_password == data.new_password:
        raise HTTPException(
            status_code=400,
            detail="New password must be different from current password",
        )

    if len(data.new_password.encode("utf-8")) > 72:
        raise HTTPException(status_code=400, detail="Password too long (max 72 bytes)")

    current_user.hashed_password = get_password_hash(data.new_password)
    db.commit()
    return {"message": "Password updated successfully"}