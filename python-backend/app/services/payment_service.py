import logging
from datetime import datetime

import stripe

from app.config import settings
from app.database import database
from app.exceptions import ErrorCode, throw_if
from app.models.enums import PaymentStatusEnum, ProductTypeEnum

logger = logging.getLogger(__name__)


class PaymentService:
    def __init__(self, db=None):
        self.db = db or database

    def _init_stripe(self):
        stripe.api_key = settings.stripe_api_key

    async def create_checkout_session(self, user_id: int, product_type: str):
        throw_if(
            product_type not in [e.value for e in ProductTypeEnum],
            ErrorCode.PARAMS_ERROR,
            "不支持的商品类型",
        )
        product = ProductTypeEnum(product_type)
        self._init_stripe()

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {"name": product.description},
                        "unit_amount": int(float(product.price) * 100),
                    },
                    "quantity": 1,
                }
            ],
            mode="payment",
            success_url=settings.stripe_success_url,
            cancel_url=settings.stripe_cancel_url,
            metadata={"user_id": str(user_id), "product_type": product_type},
        )

        now = datetime.now()
        await self.db.execute(
            query="""
                INSERT INTO payment_record
                    (userId, stripeSessionId, amount, currency, status, productType, description, createTime, updateTime)
                VALUES
                    (:userId, :stripeSessionId, :amount, :currency, :status, :productType, :description, :createTime, :updateTime)
            """,
            values={
                "userId": user_id,
                "stripeSessionId": session.id,
                "amount": float(product.price),
                "currency": "usd",
                "status": PaymentStatusEnum.PENDING.value,
                "productType": product_type,
                "description": product.description,
                "createTime": now,
                "updateTime": now,
            },
        )
        return session.url, session.id

    async def handle_webhook(self, payload: bytes, sig_header: str):
        self._init_stripe()
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.stripe_webhook_secret
            )
        except stripe.error.SignatureVerificationError as e:
            raise ValueError("Invalid Stripe signature") from e

        if event["type"] == "checkout.session.completed":
            await self._handle_checkout_completed(event["data"]["object"])

    async def _handle_checkout_completed(self, session):
        session_id = session["id"]
        payment_intent_id = session.get("payment_intent")
        user_id = int(session["metadata"]["user_id"])
        product_type = session["metadata"]["product_type"]

        existing = await self.db.fetch_one(
            query="SELECT id, status FROM payment_record WHERE stripeSessionId = :sid",
            values={"sid": session_id},
        )
        if not existing or existing["status"] == PaymentStatusEnum.SUCCEEDED.value:
            return

        now = datetime.now()
        await self.db.execute(
            query="""
                UPDATE payment_record
                SET status = :status, stripePaymentIntentId = :intentId, updateTime = :now
                WHERE stripeSessionId = :sid
            """,
            values={
                "status": PaymentStatusEnum.SUCCEEDED.value,
                "intentId": payment_intent_id,
                "now": now,
                "sid": session_id,
            },
        )

        if product_type == ProductTypeEnum.VIP_PERMANENT.value:
            await self.db.execute(
                query="UPDATE user SET userRole = 'vip', vipTime = :now WHERE id = :uid AND isDelete = 0",
                values={"now": now, "uid": user_id},
            )
            logger.info("用户 %s 已升级为永久 VIP", user_id)
