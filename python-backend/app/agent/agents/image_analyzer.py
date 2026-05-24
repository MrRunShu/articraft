from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.schemas.article import ArticleState
    from app.services.article.article_agent_service import ArticleAgentService


class ImageAnalyzerAgent:
    """配图需求分析智能体适配器：委托给 service.agent4_analyze_image_requirements"""

    async def run(self, service: "ArticleAgentService", state: "ArticleState") -> None:
        await service.agent4_analyze_image_requirements(state)
