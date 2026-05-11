from sqlalchemy import Column, BigInteger, String, DateTime, SmallInteger, Text
from sqlalchemy.sql import func

from app.database import Base


class Article(Base):
    __tablename__ = "article"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    task_id = Column("taskId", String(64), nullable=False, unique=True)
    user_id = Column("userId", BigInteger, nullable=False)
    topic = Column(String(500), nullable=False)
    style = Column(String(20), nullable=True, default="POPULAR")
    main_title = Column("mainTitle", String(200), nullable=True)
    sub_title = Column("subTitle", String(300), nullable=True)
    outline = Column(Text, nullable=True)
    content = Column(Text, nullable=True)
    full_content = Column("fullContent", Text, nullable=True)
    cover_image = Column("coverImage", String(512), nullable=True)
    images = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="PENDING")
    error_message = Column("errorMessage", Text, nullable=True)
    create_time = Column("createTime", DateTime, nullable=False, default=func.now())
    completed_time = Column("completedTime", DateTime, nullable=True)
    update_time = Column("updateTime", DateTime, nullable=False, default=func.now(), onupdate=func.now())
    is_delete = Column("isDelete", SmallInteger, nullable=False, default=0)
