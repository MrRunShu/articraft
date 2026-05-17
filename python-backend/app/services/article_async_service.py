import json
import logging
from typing import Optional

from app.database import database
from app.managers.sse_manager import sse_emitter_manager
from app.models.enums import ArticlePhaseEnum, ArticleStatusEnum, SseMessageTypeEnum
from app.schemas.article import ArticleState, OutlineResult, OutlineSection, TitleResult
from app.services.article_agent_service import ArticleAgentService
from app.services.article_service import ArticleService

logger = logging.getLogger(__name__)


class ArticleAsyncService:
    """后台协程任务：三阶段人机协作流程"""

    def _send_sse_message(self, task_id: str, msg_type: SseMessageTypeEnum, data: dict):
        payload = json.dumps({"type": msg_type.value, **data}, ensure_ascii=False)
        sse_emitter_manager.send(task_id, f"{msg_type.value}:{payload}")

    def _handle_agent_message(self, task_id: str, message: str, state: ArticleState):
        sse_emitter_manager.send(task_id, message)

    async def execute_phase1(
        self,
        task_id: str,
        topic: str,
        style: Optional[str] = None,
    ):
        """阶段1：异步生成标题方案"""
        logger.info("阶段1异步任务开始, taskId=%s", task_id)
        article_agent_service = ArticleAgentService()
        article_service = ArticleService(database)

        try:
            await article_service.update_article_status(task_id, ArticleStatusEnum.PROCESSING)
            await article_service.update_phase(task_id, ArticlePhaseEnum.TITLE_GENERATING)

            state = ArticleState()
            state.task_id = task_id
            state.topic = topic
            state.style = style or "POPULAR"

            await article_agent_service.execute_phase1_generate_titles(
                state,
                lambda message: self._handle_agent_message(task_id, message, state),
            )

            await article_service.save_title_options(task_id, state.title_options or [])
            await article_service.update_phase(task_id, ArticlePhaseEnum.TITLE_SELECTING)

            self._send_sse_message(
                task_id,
                SseMessageTypeEnum.TITLES_GENERATED,
                {
                    "titleOptions": [
                        item.model_dump(by_alias=True) for item in (state.title_options or [])
                    ]
                },
            )
            logger.info("阶段1异步任务完成, taskId=%s", task_id)
        except Exception as e:
            logger.error("阶段1异步任务失败, taskId=%s, error=%s", task_id, e)
            await article_service.update_article_status(task_id, ArticleStatusEnum.FAILED, str(e))
            self._send_sse_message(task_id, SseMessageTypeEnum.ERROR, {"message": str(e)})
            sse_emitter_manager.complete(task_id)

    async def execute_phase2(self, task_id: str):
        """阶段2：异步生成大纲"""
        logger.info("阶段2异步任务开始, taskId=%s", task_id)
        article_agent_service = ArticleAgentService()
        article_service = ArticleService(database)

        try:
            article = await article_service.get_by_task_id(task_id)
            if not article:
                raise RuntimeError("文章不存在")

            state = ArticleState()
            state.task_id = task_id
            state.style = article["style"] or "POPULAR"
            state.user_description = article["userDescription"]
            state.title = TitleResult(
                mainTitle=article["mainTitle"],
                subTitle=article["subTitle"],
            )

            await article_agent_service.execute_phase2_generate_outline(
                state,
                lambda message: self._handle_agent_message(task_id, message, state),
            )
            await article_service.save_outline(
                task_id, state.outline.sections if state.outline else []
            )
            await article_service.update_phase(task_id, ArticlePhaseEnum.OUTLINE_EDITING)

            self._send_sse_message(
                task_id,
                SseMessageTypeEnum.OUTLINE_GENERATED,
                {
                    "outline": [
                        item.model_dump()
                        for item in (state.outline.sections if state.outline else [])
                    ]
                },
            )
            logger.info("阶段2异步任务完成, taskId=%s", task_id)
        except Exception as e:
            logger.error("阶段2异步任务失败, taskId=%s, error=%s", task_id, e)
            await article_service.update_article_status(task_id, ArticleStatusEnum.FAILED, str(e))
            self._send_sse_message(task_id, SseMessageTypeEnum.ERROR, {"message": str(e)})
            sse_emitter_manager.complete(task_id)

    async def execute_phase3(self, task_id: str):
        """阶段3：异步生成正文与配图"""
        logger.info("阶段3异步任务开始, taskId=%s", task_id)
        article_agent_service = ArticleAgentService()
        article_service = ArticleService(database)

        try:
            article = await article_service.get_by_task_id(task_id)
            if not article:
                raise RuntimeError("文章不存在")

            outline_data = json.loads(article["outline"]) if article["outline"] else []
            enabled_methods = (
                json.loads(article["enabledImageMethods"])
                if article["enabledImageMethods"]
                else None
            )

            state = ArticleState()
            state.task_id = task_id
            state.style = article["style"] or "POPULAR"
            state.enabled_image_methods = enabled_methods
            state.title = TitleResult(
                mainTitle=article["mainTitle"],
                subTitle=article["subTitle"],
            )
            state.outline = OutlineResult(
                sections=[OutlineSection(**item) for item in outline_data]
            )

            await article_agent_service.execute_phase3_generate_content(
                state,
                lambda message: self._handle_agent_message(task_id, message, state),
            )
            await article_service.save_article_content(task_id, state)
            await article_service.update_article_status(task_id, ArticleStatusEnum.COMPLETED)

            self._send_sse_message(
                task_id,
                SseMessageTypeEnum.ALL_COMPLETE,
                {"taskId": task_id},
            )
            sse_emitter_manager.complete(task_id)
            logger.info("阶段3异步任务完成, taskId=%s", task_id)
        except Exception as e:
            logger.error("阶段3异步任务失败, taskId=%s, error=%s", task_id, e)
            await article_service.update_article_status(task_id, ArticleStatusEnum.FAILED, str(e))
            self._send_sse_message(task_id, SseMessageTypeEnum.ERROR, {"message": str(e)})
            sse_emitter_manager.complete(task_id)


article_async_service = ArticleAsyncService()
