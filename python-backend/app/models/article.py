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
    user_description = Column("userDescription", Text, nullable=True, comment="用户补充描述")
    enabled_image_methods = Column("enabledImageMethods", Text, nullable=True, comment="允许的配图方式列表（JSON格式）")
    title_options = Column("titleOptions", Text, nullable=True, comment="标题方案列表（JSON格式）")
    phase = Column(
        String(50),
        nullable=False,
        default="PENDING",
        comment="阶段：PENDING/TITLE_GENERATING/TITLE_SELECTING/OUTLINE_GENERATING/OUTLINE_EDITING/CONTENT_GENERATING",
    )
    status = Column(String(20), nullable=False, default="PENDING")
    error_message = Column("errorMessage", Text, nullable=True)
    create_time = Column("createTime", DateTime, nullable=False, default=func.now())
    completed_time = Column("completedTime", DateTime, nullable=True)
    update_time = Column("updateTime", DateTime, nullable=False, default=func.now(), onupdate=func.now())
    is_delete = Column("isDelete", SmallInteger, nullable=False, default=0)
