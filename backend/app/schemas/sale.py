from pydantic import BaseModel


class SaleItemCreate(BaseModel):
    product_id: str
    quantity: float
    unit: str | None = None


class SaleCreate(BaseModel):
    items: list[SaleItemCreate]
    customer_id: str | None = None
    payment_status: str = "paid"
    amount_paid: float = 0.0


class SaleResponse(BaseModel):
    id: str
    total_amount: float

    class Config:
        from_attributes = True


class BulkSaleItem(BaseModel):
    id: str  # <-- changed from UUID to str
    qty: float


class BulkSaleCreate(BaseModel):
    items: list[BulkSaleItem]
    customer_id: str | None = None
    payment_status: str = "paid"
    amount_paid: float = 0.0
