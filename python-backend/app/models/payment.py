from sqlalchemy import Column, BigInteger, String, DateTime, Numeric
from sqlalchemy.sql import func

from app.database import Base


class PaymentRecord(Base):
    __tablename__ = "payment_record"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column("userId", BigInteger, nullable=False)
    stripe_session_id = Column("stripeSessionId", String(128), nullable=True)
    stripe_payment_intent_id = Column("stripePaymentIntentId", String(128), nullable=True)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(8), default="usd")
    status = Column(String(32), nullable=False)
    product_type = Column("productType", String(32), nullable=False)
    description = Column(String(256), nullable=True)
    refund_time = Column("refundTime", DateTime, nullable=True)
    refund_reason = Column("refundReason", String(512), nullable=True)
    create_time = Column("createTime", DateTime, nullable=False, default=func.now())
    update_time = Column("updateTime", DateTime, nullable=False, default=func.now(), onupdate=func.now())
