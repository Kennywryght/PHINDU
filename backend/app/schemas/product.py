"""Product Pydantic schemas."""

from pydantic import BaseModel, Field


class ProductCreate(BaseModel):
    """Schema for creating a new product."""

    name: str = Field(..., min_length=1, max_length=200)
    category: str | None = None
    type: str = Field(..., description='"variant" or "bulk"')
    unit: str = Field(..., description='"kg", "g", "piece"')
    selling_price: float = Field(0, ge=0, description="Selling price (0 for parent products)")
    purchase_price: float = Field(0, ge=0, description="Purchase price (0 for parent products)")
    stock_qty: float = Field(0, ge=0, description="Stock quantity")
    parent_id: str | None = None
    low_stock_threshold: float = Field(5, ge=0)


class ProductOut(BaseModel):
    """Schema for product output."""

    id: str
    shop_id: str
    name: str
    category: str | None
    type: str
    unit: str
    selling_price: float
    purchase_price: float
    stock_qty: float
    archived: bool = False
    is_deleted: bool = False
    parent_id: str | None = None
    low_stock_threshold: float = 5
    # Computed fields (set by route)
    is_parent: bool = False
    variant_count: int = 0

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
    low_stock_threshold: float | None = None


class VariantSummary(BaseModel):
    """Minimal variant info for picker UI."""

    id: str
    name: str
    unit: str
    selling_price: float
    stock_qty: float

    class Config:
        from_attributes = True


# ── Tier 3.3: Bulk creation (Variant Wizard) ────────────────────


class BulkVariantItem(BaseModel):
    """One variant row inside a bulk product creation request."""

    name: str = Field(..., min_length=1, max_length=200)
    selling_price: float = Field(..., gt=0)
    purchase_price: float = Field(0, ge=0)
    stock_qty: float = Field(0, ge=0)
    low_stock_threshold: float = Field(5, ge=0)


class BulkProductCreate(BaseModel):
    """
    Create one parent product + N variants in a single atomic request.

    If `has_variants` is False, the wizard is treated as "create a single
    standalone product" — in that case the parent record itself carries
    the price/stock (like a normal ProductCreate).
    """

    name: str = Field(..., min_length=1, max_length=200)
    category: str | None = None
    type: str = Field("variant", description='"variant" or "bulk"')
    unit: str = Field("piece", description='"kg", "g", "piece"')
    low_stock_threshold: float = Field(5, ge=0)

    has_variants: bool = True
    # Only used when has_variants = False
    selling_price: float = Field(0, ge=0)
    purchase_price: float = Field(0, ge=0)
    stock_qty: float = Field(0, ge=0)

    # Only used when has_variants = True
    variants: list[BulkVariantItem] = Field(default_factory=list)