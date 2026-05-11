from enum import Enum


class ArticleStatusEnum(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ImageMethodEnum(str, Enum):
    PEXELS = "PEXELS"
    PICSUM = "PICSUM"
    NANO_BANANA = "NANO_BANANA"
    MERMAID = "MERMAID"
    ICONIFY = "ICONIFY"
    EMOJI_PACK = "EMOJI_PACK"
    SVG_DIAGRAM = "SVG_DIAGRAM"

    def is_ai_generated(self) -> bool:
        return self in [
            ImageMethodEnum.NANO_BANANA,
            ImageMethodEnum.MERMAID,
            ImageMethodEnum.SVG_DIAGRAM,
        ]

    def is_fallback(self) -> bool:
        return self == ImageMethodEnum.PICSUM

    @classmethod
    def get_default_search_method(cls):
        return cls.PEXELS

    @classmethod
    def get_fallback_method(cls):
        return cls.PICSUM


class ArticleStyleEnum(str, Enum):
    POPULAR = "POPULAR"       # 爆款新媒体
    PROFESSIONAL = "PROFESSIONAL"  # 专业深度
    HUMOROUS = "HUMOROUS"     # 轻松幽默
    STORYTELLING = "STORYTELLING"  # 故事叙述


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
