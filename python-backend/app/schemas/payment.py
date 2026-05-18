from pydantic import BaseModel, Field


class CreateCheckoutRequest(BaseModel):
    product_type: str = Field(..., alias="productType")

    class Config:
        populate_by_name = True


class CheckoutVO(BaseModel):
    checkout_url: str = Field(..., alias="checkoutUrl")
    session_id: str = Field(..., alias="sessionId")

    class Config:
        populate_by_name = True
