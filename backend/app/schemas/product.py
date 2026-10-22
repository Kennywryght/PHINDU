"""Product Pydantic schemas."""

from pydantic import BaseModel, Field


class ProductCreate(BaseModel):
    """Schema for creating a new product."""

    name: str
    category: str | None = None
    type: str = Field(..., description='"variant" or "bulk"')
    unit: str = Field(..., description='"kg", "g", "piece"')
    selling_price: float = Field(..., gt=0, description="Selling price must be greater than 0")
    purchase_price: float = Field(..., gt=0, description="Purchase price must be greater than 0")
    stock_qty: float = Field(..., ge=0, description="Stock quantity must be a non-negative number")
    parent_id: str | None = None


class ProductOut(BaseModel):
    """Schema for product output."""

    id: str
    name: str
    category: str | None
    type: str
    unit: str
    selling_price: float
    purchase_price: float
    stock_qty: float
    archived: bool = False

    class Config:
        from_attributes = True


class ProductUpdate(BaseModel):
    """Schema for updating product fields."""

    name: str | None = None
    category: str | None = None
    type: str | None = None
    unit: str | None = None
    selling_price: float | None = None
    purchase_price: float | None = None
    stock_qty: float | None = None
