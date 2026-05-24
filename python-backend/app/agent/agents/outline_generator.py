from __future__ import annotations
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from app.schemas.article import ArticleState
    from app.services.article.article_agent_service import ArticleAgentService


class OutlineGeneratorAgent:
    """大纲生成智能体适配器：委托给 service.agent2_generate_outline（需流式输出）"""

    async def run(
        self,
        service: "ArticleAgentService",
        state: "ArticleState",
        stream_handler: Callable[[str], None],
    ) -> None:
        await service.agent2_generate_outline(state, stream_handler)
