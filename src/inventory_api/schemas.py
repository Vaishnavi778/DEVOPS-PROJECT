from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ItemInput(BaseModel):
    sku: str = Field(min_length=2, max_length=64, pattern=r"^[A-Z0-9][A-Z0-9_-]*$")
    name: str = Field(min_length=1, max_length=160)
    quantity: int = Field(ge=0)
    unit_price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)


class ItemOutput(ItemInput):
    model_config = ConfigDict(from_attributes=True)

    id: int
