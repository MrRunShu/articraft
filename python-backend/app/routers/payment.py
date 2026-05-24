from fastapi import APIRouter, Depends, Header, HTTPException, Request
from databases import Database

from app.database import get_db
from app.deps import require_login
from app.schemas.common import BaseResponse
from app.schemas.payment import CheckoutVO, CreateCheckoutRequest
from app.schemas.user import LoginUserVO
from app.services.user.payment_service import PaymentService

router = APIRouter(prefix="/payment", tags=["支付管理"])


@router.post("/checkout", response_model=BaseResponse[CheckoutVO])
async def create_checkout(
    request: CreateCheckoutRequest,
    db: Database = Depends(get_db),
    current_user: LoginUserVO = Depends(require_login),
):
    service = PaymentService(db)
    checkout_url, session_id = await service.create_checkout_session(
        current_user.id, request.product_type
    )
    vo = CheckoutVO(checkoutUrl=checkout_url, sessionId=session_id)
    return BaseResponse.success(data=vo)


@router.post("/webhook/stripe")
async def stripe_webhook(
    request: Request,
    db: Database = Depends(get_db),
    stripe_signature: str = Header(None, alias="stripe-signature"),
):
    payload = await request.body()
    service = PaymentService(db)
    try:
        await service.handle_webhook(payload, stripe_signature)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "ok"}
