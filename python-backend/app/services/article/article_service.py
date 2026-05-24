import json
import logging
import uuid
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import insert, update, select, func, and_

from app.constants.user import UserConstant
from app.database import database
from app.exceptions import ErrorCode, throw_if, throw_if_not
from app.models.article import Article
from app.models.enums import ArticlePhaseEnum, ArticleStatusEnum, ImageMethodEnum
from app.schemas.article import (
    ArticleQueryRequest,
    ArticleState,
    ArticleVO,
    OutlineSection,
    TitleOption,
)
from app.schemas.user import LoginUserVO

logger = logging.getLogger(__name__)


class ArticleService:
    def __init__(self, db=None):
        self.db = db or database

    async def create_article_task_with_quota_check(
        self,
        topic: str,
        login_user: LoginUserVO,
        style: str = "POPULAR",
        enabled_image_methods: Optional[List[str]] = None,
        language: str = 'zh',   # 新增
    ) -> str:
        """创建文章任务，返回 taskId"""
        if login_user.user_role not in (UserConstant.VIP_ROLE, UserConstant.ADMIN_ROLE):
            count = await self.db.fetch_val(
                select(func.count(Article.id)).where(
                    and_(Article.user_id == login_user.id, Article.is_delete == 0)
                )
            )
            throw_if(
                count >= UserConstant.DEFAULT_QUOTA,
                ErrorCode.NO_AUTH_ERROR,
                f"免费用户最多创建 {UserConstant.DEFAULT_QUOTA} 篇文章，请升级为 VIP",
            )
            vip_only = {ImageMethodEnum.NANO_BANANA.value, ImageMethodEnum.SVG_DIAGRAM.value}
            if enabled_image_methods:
                enabled_image_methods = [m for m in enabled_image_methods if m not in vip_only]

        task_id = str(uuid.uuid4())
        now = datetime.now()
        await self.db.execute(
            insert(Article).values(
                task_id=task_id,
                user_id=login_user.id,
                topic=topic,
                style=style,
                language=language,   # 新增
                status=ArticleStatusEnum.PENDING.value,
                phase=ArticlePhaseEnum.PENDING.value,
                enabled_image_methods=(
                    json.dumps(enabled_image_methods, ensure_ascii=False)
                    if enabled_image_methods
                    else None
                ),
                create_time=now,
                update_time=now,
                is_delete=0,
            )
        )
        return task_id

    async def get_by_task_id(self, task_id: str):
        """通过 taskId 查询文章记录"""
        return await self.db.fetch_one(
            select(Article).where(
                and_(Article.task_id == task_id, Article.is_delete == 0)
            )
        )

    def _check_article_permission(self, article, login_user: LoginUserVO):
        throw_if(
            article["userId"] != login_user.id and login_user.user_role != UserConstant.ADMIN_ROLE,
            ErrorCode.NO_AUTH_ERROR,
            "无权限操作该文章",
        )

    async def update_phase(self, task_id: str, phase: ArticlePhaseEnum):
        """更新文章阶段（含合法性校验）"""
        article = await self.get_by_task_id(task_id)
        if not article:
            logger.error("文章记录不存在, taskId=%s", task_id)
            return

        current_phase_value = article["phase"] or ArticlePhaseEnum.PENDING.value
        try:
            current_phase = ArticlePhaseEnum(current_phase_value)
        except ValueError as exc:
            raise Exception("当前阶段非法") from exc

        if current_phase != phase and not current_phase.can_transition_to(phase):
            raise Exception(f"非法阶段流转: {current_phase.value} -> {phase.value}")

        await self.db.execute(
            update(Article).where(Article.task_id == task_id).values(phase=phase.value)
        )

    async def save_title_options(self, task_id: str, title_options: List[TitleOption]):
        """保存标题方案列表"""
        await self.db.execute(
            update(Article).where(Article.task_id == task_id).values(
                title_options=json.dumps(
                    [item.model_dump(by_alias=True) for item in title_options],
                    ensure_ascii=False,
                )
            )
        )

    async def confirm_title(
        self,
        task_id: str,
        selected_main_title: str,
        selected_sub_title: str,
        user_description: Optional[str],
        login_user: LoginUserVO,
    ):
        """确认标题并进入大纲生成阶段"""
        article = await self.get_by_task_id(task_id)
        throw_if_not(article, ErrorCode.NOT_FOUND_ERROR, "文章不存在")
        self._check_article_permission(article, login_user)
        throw_if(
            article["phase"] != ArticlePhaseEnum.TITLE_SELECTING.value,
            ErrorCode.OPERATION_ERROR,
            "当前阶段不允许确认标题",
        )
        await self.db.execute(
            update(Article).where(Article.task_id == task_id).values(
                main_title=selected_main_title,
                sub_title=selected_sub_title,
                user_description=user_description,
                phase=ArticlePhaseEnum.OUTLINE_GENERATING.value,
            )
        )

    async def save_outline(self, task_id: str, outline: List[OutlineSection]):
        """保存大纲内容（不推进阶段）"""
        await self.db.execute(
            update(Article).where(Article.task_id == task_id).values(
                outline=json.dumps([item.model_dump() for item in outline], ensure_ascii=False)
            )
        )

    async def confirm_outline(
        self,
        task_id: str,
        outline: List[OutlineSection],
        login_user: LoginUserVO,
    ):
        """确认大纲并进入正文生成阶段"""
        article = await self.get_by_task_id(task_id)
        throw_if_not(article, ErrorCode.NOT_FOUND_ERROR, "文章不存在")
        self._check_article_permission(article, login_user)
        throw_if(
            article["phase"] != ArticlePhaseEnum.OUTLINE_EDITING.value,
            ErrorCode.OPERATION_ERROR,
            "当前阶段不允许确认大纲",
        )
        await self.db.execute(
            update(Article).where(Article.task_id == task_id).values(
                outline=json.dumps([item.model_dump() for item in outline], ensure_ascii=False),
                phase=ArticlePhaseEnum.CONTENT_GENERATING.value,
            )
        )

    async def ai_modify_outline(
        self,
        task_id: str,
        modify_suggestion: str,
        login_user: LoginUserVO,
    ) -> List[OutlineSection]:
        """AI 修改大纲（同步返回修改结果）"""
        article = await self.get_by_task_id(task_id)
        throw_if_not(article, ErrorCode.NOT_FOUND_ERROR, "文章不存在")
        self._check_article_permission(article, login_user)
        throw_if(
            article["phase"] != ArticlePhaseEnum.OUTLINE_EDITING.value,
            ErrorCode.OPERATION_ERROR,
            "当前阶段不允许 AI 修改大纲",
        )
        throw_if(not article["outline"], ErrorCode.OPERATION_ERROR, "当前文章尚未生成大纲")

        current_outline = [OutlineSection(**item) for item in json.loads(article["outline"])]

        from app.services.article.article_agent_service import ArticleAgentService
        agent_service = ArticleAgentService()
        modified_outline = await agent_service.ai_modify_outline(
            main_title=article["mainTitle"],
            sub_title=article["subTitle"],
            current_outline=current_outline,
            modify_suggestion=modify_suggestion,
            task_id=task_id,
            language=article.get("language", "zh"),   # 新增
        )
        await self.db.execute(
            update(Article).where(Article.task_id == task_id).values(
                outline=json.dumps(
                    [item.model_dump() for item in modified_outline], ensure_ascii=False
                )
            )
        )
        return modified_outline

    async def update_article_status(
        self,
        task_id: str,
        status: ArticleStatusEnum,
        error_message: Optional[str] = None,
    ):
        update_values = {"status": status.value}
        if status == ArticleStatusEnum.COMPLETED:
            update_values["completed_time"] = datetime.now()
        elif status == ArticleStatusEnum.FAILED:
            update_values["error_message"] = error_message
        await self.db.execute(
            update(Article).where(Article.task_id == task_id).values(**update_values)
        )

    async def save_article_content(self, task_id: str, state: ArticleState):
        """将智能体生成结果持久化"""
        cover_image = None
        if state.images:
            cover = next((img for img in state.images if img.position == 1), None)
            if cover:
                cover_image = cover.url

        await self.db.execute(
            update(Article).where(Article.task_id == task_id).values(
                main_title=state.title.main_title,
                sub_title=state.title.sub_title,
                outline=json.dumps(
                    [s.model_dump() for s in state.outline.sections], ensure_ascii=False
                ),
                content=state.content,
                full_content=state.full_content,
                cover_image=cover_image,
                images=json.dumps(
                    [img.model_dump(by_alias=True) for img in state.images], ensure_ascii=False
                ),
            )
        )

    async def get_article_detail(self, task_id: str, login_user: LoginUserVO) -> ArticleVO:
        row = await self.get_by_task_id(task_id)
        throw_if_not(row, ErrorCode.NOT_FOUND_ERROR, "文章不存在")
        throw_if(
            row["userId"] != login_user.id and login_user.user_role != UserConstant.ADMIN_ROLE,
            ErrorCode.NO_AUTH_ERROR,
            "无权限访问该文章",
        )
        return self._row_to_vo(row)

    async def list_article_by_page(
        self, request: ArticleQueryRequest, login_user: LoginUserVO
    ) -> Tuple[List[ArticleVO], int]:
        conditions = [Article.is_delete == 0]

        if login_user.user_role != UserConstant.ADMIN_ROLE:
            conditions.append(Article.user_id == login_user.id)
        elif request.user_id:
            conditions.append(Article.user_id == request.user_id)

        if request.status:
            conditions.append(Article.status == request.status)
        if request.topic:
            conditions.append(Article.topic.like(f"%{request.topic}%"))

        total = await self.db.fetch_val(
            select(func.count(Article.id)).where(and_(*conditions))
        )
        offset = (request.current - 1) * request.page_size
        rows = await self.db.fetch_all(
            select(Article)
            .where(and_(*conditions))
            .order_by(Article.create_time.desc())
            .offset(offset)
            .limit(request.page_size)
        )
        return [self._row_to_vo(r) for r in rows], total

    async def delete_article(self, article_id: int, login_user: LoginUserVO) -> bool:
        row = await self.db.fetch_one(
            select(Article).where(
                and_(Article.id == article_id, Article.is_delete == 0)
            )
        )
        throw_if_not(row, ErrorCode.NOT_FOUND_ERROR, "文章不存在")
        throw_if(
            row["userId"] != login_user.id and login_user.user_role != UserConstant.ADMIN_ROLE,
            ErrorCode.NO_AUTH_ERROR,
            "无权限删除该文章",
        )
        await self.db.execute(
            update(Article).where(Article.id == article_id).values(is_delete=1)
        )
        return True

    def _row_to_vo(self, row) -> ArticleVO:
        row_dict = dict(row)
        return ArticleVO(
            id=row["id"],
            taskId=row["taskId"],
            userId=row["userId"],
            topic=row["topic"],
            style=row_dict.get("style", "POPULAR"),
            mainTitle=row["mainTitle"],
            subTitle=row["subTitle"],
            titleOptions=json.loads(row["titleOptions"]) if row_dict.get("titleOptions") else None,
            outline=json.loads(row["outline"]) if row["outline"] else None,
            content=row["content"],
            fullContent=row["fullContent"],
            coverImage=row["coverImage"],
            images=json.loads(row["images"]) if row["images"] else None,
            status=row["status"],
            phase=row_dict.get("phase"),
            errorMessage=row["errorMessage"],
            createTime=row["createTime"].isoformat(),
            completedTime=row["completedTime"].isoformat() if row["completedTime"] else None,
        )
