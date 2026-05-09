import json
import logging
from typing import Any, Dict

from app.database import database
from app.managers.sse_manager import sse_emitter_manager
from app.models.enums import ArticleStatusEnum, SseMessageTypeEnum
from app.schemas.article import ArticleState
from app.services.article_agent_service import ArticleAgentService
from app.services.article_service import ArticleService

logger = logging.getLogger(__name__)


class ArticleAsyncService:
    """后台协程任务：连接 Router 和 AgentService"""

    async def execute_article_generation(self, task_id: str, topic: str):
        article_service = ArticleService(database)
        article_agent_service = ArticleAgentService()
        try:
            await article_service.update_article_status(task_id, ArticleStatusEnum.PROCESSING)

            state = ArticleState()
            state.task_id = task_id
            state.topic = topic

            await article_agent_service.execute_article_generation(
                state,
                lambda message: self._send_sse(task_id, message, state),
            )

            await article_service.save_article_content(task_id, state)
            await article_service.update_article_status(task_id, ArticleStatusEnum.COMPLETED)

            sse_emitter_manager.send(
                task_id,
                json.dumps({"type": SseMessageTypeEnum.ALL_COMPLETE.value, "taskId": task_id}, ensure_ascii=False),
            )
            sse_emitter_manager.complete(task_id)
        except Exception as e:
            logger.error(f"异步任务失败, taskId={task_id}, error={e}")
            await article_service.update_article_status(
                task_id, ArticleStatusEnum.FAILED, str(e)
            )
            sse_emitter_manager.send(
                task_id,
                json.dumps({"type": SseMessageTypeEnum.ERROR.value, "message": str(e)}, ensure_ascii=False),
            )
            sse_emitter_manager.complete(task_id)

    def _send_sse(self, task_id: str, message: str, state: ArticleState):
        """将 AgentService 的原始消息转换成结构化 JSON 推送"""
        data = self._build_message_data(message, state)
        sse_emitter_manager.send(task_id, json.dumps(data, ensure_ascii=False))

    def _build_message_data(self, message: str, state: ArticleState) -> Dict[str, Any]:
        prefix2 = SseMessageTypeEnum.AGENT2_STREAMING.get_streaming_prefix()
        prefix3 = SseMessageTypeEnum.AGENT3_STREAMING.get_streaming_prefix()
        prefix_img = SseMessageTypeEnum.IMAGE_COMPLETE.get_streaming_prefix()

        if message.startswith(prefix2):
            return {"type": SseMessageTypeEnum.AGENT2_STREAMING.value, "content": message[len(prefix2):]}
        if message.startswith(prefix3):
            return {"type": SseMessageTypeEnum.AGENT3_STREAMING.value, "content": message[len(prefix3):]}
        if message.startswith(prefix_img):
            return {"type": SseMessageTypeEnum.IMAGE_COMPLETE.value, "image": json.loads(message[len(prefix_img):])}

        complete_map = {
            SseMessageTypeEnum.AGENT1_COMPLETE.value: lambda s: {
                "type": SseMessageTypeEnum.AGENT1_COMPLETE.value,
                "title": s.title.model_dump(by_alias=True) if s.title else None,
            },
            SseMessageTypeEnum.AGENT2_COMPLETE.value: lambda s: {
                "type": SseMessageTypeEnum.AGENT2_COMPLETE.value,
                "outline": [sec.model_dump() for sec in s.outline.sections] if s.outline else None,
            },
            SseMessageTypeEnum.AGENT3_COMPLETE.value: lambda s: {
                "type": SseMessageTypeEnum.AGENT3_COMPLETE.value,
            },
            SseMessageTypeEnum.AGENT4_COMPLETE.value: lambda s: {
                "type": SseMessageTypeEnum.AGENT4_COMPLETE.value,
                "imageRequirements": [r.model_dump(by_alias=True) for r in s.image_requirements] if s.image_requirements else None,
            },
            SseMessageTypeEnum.AGENT5_COMPLETE.value: lambda s: {
                "type": SseMessageTypeEnum.AGENT5_COMPLETE.value,
            },
            SseMessageTypeEnum.MERGE_COMPLETE.value: lambda s: {
                "type": SseMessageTypeEnum.MERGE_COMPLETE.value,
            },
        }
        builder = complete_map.get(message)
        if builder:
            return builder(state)
        return {"type": message}


article_async_service = ArticleAsyncService()
