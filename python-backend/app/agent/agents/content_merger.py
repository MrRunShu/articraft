from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.schemas.article import ArticleState
    from app.services.article.article_agent_service import ArticleAgentService


class ContentMergerAgent:
    """图文合并智能体适配器：委托给 service.merge_images_into_content（同步）"""

    def run(self, service: "ArticleAgentService", state: "ArticleState") -> None:
        service.merge_images_into_content(state)
