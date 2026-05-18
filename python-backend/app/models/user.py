from sqlalchemy import Column, BigInteger, String, DateTime, SmallInteger
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    __tablename__ = "user"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_account = Column("userAccount", String(256), nullable=False, unique=True)
    user_password = Column("userPassword", String(512), nullable=False)
    user_name = Column("userName", String(256), nullable=True)
    user_avatar = Column("userAvatar", String(1024), nullable=True)
    user_profile = Column("userProfile", String(512), nullable=True)
    user_role = Column("userRole", String(256), nullable=False, default="user")
    vip_time = Column("vipTime", DateTime, nullable=True)

    edit_time = Column("editTime", DateTime, nullable=False, default=func.now())
    create_time = Column("createTime", DateTime, nullable=False, default=func.now())
    update_time = Column("updateTime", DateTime, nullable=False, default=func.now(), onupdate=func.now())
    is_delete = Column("isDelete", SmallInteger, nullable=False, default=0)
