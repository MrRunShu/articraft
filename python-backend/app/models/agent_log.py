from sqlalchemy import Column, BigInteger, String, DateTime, Integer, Text, SmallInteger
from sqlalchemy.sql import func

from app.database import Base


class AgentLog(Base):
    """智能体执行日志表"""

    __tablename__ = "agent_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    task_id = Column("taskId", String(64), nullable=False)
    agent_name = Column("agentName", String(50), nullable=False)
    start_time = Column("startTime", DateTime, nullable=False)
    end_time = Column("endTime", DateTime, nullable=True)
    duration_ms = Column("durationMs", Integer, nullable=True)
    status = Column("status", String(20), nullable=False)
    error_message = Column("errorMessage", Text, nullable=True)
    prompt = Column("prompt", Text, nullable=True)
    input_data = Column("inputData", Text, nullable=True)
    output_data = Column("outputData", Text, nullable=True)
    create_time = Column("createTime", DateTime, nullable=False, default=func.now())
    update_time = Column(
        "updateTime", DateTime, nullable=False, default=func.now(), onupdate=func.now()
    )
    is_delete = Column("isDelete", SmallInteger, nullable=False, default=0)
