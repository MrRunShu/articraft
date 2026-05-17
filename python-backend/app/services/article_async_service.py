import logging

from app.database import database
from app.managers.sse_manager import sse_emitter_manager
from app.models.enums import ArticleStatusEnum, SseMessageTypeEnum
from app.schemas.article import ArticleState
from app.services.article_agent_service import ArticleAgentService
from app.services.article_service import ArticleService

logger = logging.getLogger(__name__)


class ArticleAsyncService:
    """后台协程任务：连接 Router 和 AgentService"""

    async def execute_article_generation(self, task_id: str, topic: str, style: str = "POPULAR"):
        article_service = ArticleService(database)
        article_agent_service = ArticleAgentService()
        try:
            await article_service.update_article_status(task_id, ArticleStatusEnum.PROCESSING)

            state = ArticleState()
            state.task_id = task_id
            state.topic = topic
            state.style = style

            await article_agent_service.execute_article_generation(
                state,
                lambda message: sse_emitter_manager.send(task_id, message),
            )

            await article_service.save_article_content(task_id, state)
            await article_service.update_article_status(task_id, ArticleStatusEnum.COMPLETED)

            sse_emitter_manager.send(task_id, SseMessageTypeEnum.ALL_COMPLETE.value)
            sse_emitter_manager.complete(task_id)
        except Exception as e:
            logger.error(f"异步任务失败, taskId={task_id}, error={e}")
            await article_service.update_article_status(
                task_id, ArticleStatusEnum.FAILED, str(e)
            )
            sse_emitter_manager.send(task_id, f"{SseMessageTypeEnum.ERROR.get_streaming_prefix()}{e}")
            sse_emitter_manager.complete(task_id)


article_async_service = ArticleAsyncService()
