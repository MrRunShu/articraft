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


class ArticlePhaseEnum(str, Enum):
    """文章阶段枚举（Day5 用户交互增强）"""

    PENDING = "PENDING"
    TITLE_GENERATING = "TITLE_GENERATING"
    TITLE_SELECTING = "TITLE_SELECTING"
    OUTLINE_GENERATING = "OUTLINE_GENERATING"
    OUTLINE_EDITING = "OUTLINE_EDITING"
    CONTENT_GENERATING = "CONTENT_GENERATING"

    def can_transition_to(self, target_phase: "ArticlePhaseEnum") -> bool:
        transitions = {
            ArticlePhaseEnum.PENDING: {ArticlePhaseEnum.TITLE_GENERATING},
            ArticlePhaseEnum.TITLE_GENERATING: {ArticlePhaseEnum.TITLE_SELECTING},
            ArticlePhaseEnum.TITLE_SELECTING: {ArticlePhaseEnum.OUTLINE_GENERATING},
            ArticlePhaseEnum.OUTLINE_GENERATING: {ArticlePhaseEnum.OUTLINE_EDITING},
            ArticlePhaseEnum.OUTLINE_EDITING: {ArticlePhaseEnum.CONTENT_GENERATING},
            ArticlePhaseEnum.CONTENT_GENERATING: set(),
        }
        return target_phase in transitions.get(self, set())


class SseMessageTypeEnum(str, Enum):
    AGENT1_COMPLETE = "AGENT1_COMPLETE"
    TITLES_GENERATED = "TITLES_GENERATED"
    AGENT2_STREAMING = "AGENT2_STREAMING"
    AGENT2_COMPLETE = "AGENT2_COMPLETE"
    OUTLINE_GENERATED = "OUTLINE_GENERATED"
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


class PaymentStatusEnum(str, Enum):
    """支付状态枚举"""

    PENDING = "PENDING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class ProductTypeEnum(str, Enum):
    """产品类型枚举"""

    VIP_PERMANENT = "VIP_PERMANENT"

    @property
    def description(self) -> str:
        descriptions = {
            ProductTypeEnum.VIP_PERMANENT: "永久会员",
        }
        return descriptions[self]

    @property
    def price(self) -> str:
        prices = {
            ProductTypeEnum.VIP_PERMANENT: "199.00",
        }
        return prices[self]
