from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.schemas.article import ArticleState
    from app.services.article.article_agent_service import ArticleAgentService


class TitleGeneratorAgent:
    """标题生成智能体适配器：委托给 service.agent1_generate_title_options"""

    async def run(self, service: "ArticleAgentService", state: "ArticleState") -> None:
        await service.agent1_generate_title_options(state)
