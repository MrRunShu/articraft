from enum import Enum


class ArticleStatusEnum(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ImageMethodEnum(str, Enum):
    PEXELS = "PEXELS"
    PICSUM = "PICSUM"


class SseMessageTypeEnum(str, Enum):
    AGENT1_COMPLETE = "AGENT1_COMPLETE"
    AGENT2_STREAMING = "AGENT2_STREAMING"
    AGENT2_COMPLETE = "AGENT2_COMPLETE"
    AGENT3_STREAMING = "AGENT3_STREAMING"
    AGENT3_COMPLETE = "AGENT3_COMPLETE"
    AGENT4_COMPLETE = "AGENT4_COMPLETE"
    IMAGE_COMPLETE = "IMAGE_COMPLETE"
    AGENT5_COMPLETE = "AGENT5_COMPLETE"
    MERGE_COMPLETE = "MERGE_COMPLETE"
    ALL_COMPLETE = "ALL_COMPLETE"
    ERROR = "ERROR"

    def get_streaming_prefix(self) -> str:
        return f"{self.value}:"
