from __future__ import annotations
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from app.schemas.article import ArticleState
    from app.services.article.article_agent_service import ArticleAgentService


class ContentGeneratorAgent:
    """正文生成智能体适配器：委托给 service.agent3_generate_content（需流式输出）"""

    async def run(
        self,
        service: "ArticleAgentService",
        state: "ArticleState",
        stream_handler: Callable[[str], None],
    ) -> None:
        await service.agent3_generate_content(state, stream_handler)
