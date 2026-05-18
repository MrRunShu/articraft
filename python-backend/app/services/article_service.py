import json
import logging
import uuid
from datetime import datetime
from typing import List, Optional, Tuple

from app.constants.user import UserConstant
from app.database import database
from app.exceptions import ErrorCode, throw_if, throw_if_not
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
    ) -> str:
        """创建文章任务，返回 taskId"""
        if login_user.user_role not in (UserConstant.VIP_ROLE, UserConstant.ADMIN_ROLE):
            count = await self.db.fetch_val(
                query="SELECT COUNT(*) FROM article WHERE userId = :uid AND isDelete = 0",
                values={"uid": login_user.id},
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
        await self.db.execute(
            query="""
                INSERT INTO article (taskId, userId, topic, style, status, phase, enabledImageMethods, createTime)
                VALUES (:taskId, :userId, :topic, :style, :status, :phase, :enabledImageMethods, :createTime)
            """,
            values={
                "taskId": task_id,
                "userId": login_user.id,
                "topic": topic,
                "style": style,
                "status": ArticleStatusEnum.PENDING.value,
                "phase": ArticlePhaseEnum.PENDING.value,
                "enabledImageMethods": json.dumps(enabled_image_methods, ensure_ascii=False) if enabled_image_methods else None,
                "createTime": datetime.now(),
            },
        )
        return task_id

    async def get_by_task_id(self, task_id: str):
        """通过 taskId 查询文章记录"""
        return await self.db.fetch_one(
            query="SELECT * FROM article WHERE taskId = :taskId AND isDelete = 0",
            values={"taskId": task_id},
        )

    def _check_article_permission(self, article, login_user: LoginUserVO):
        throw_if(
            article["userId"] != login_user.id and login_user.user_role != "admin",
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
            query="UPDATE article SET phase = :phase WHERE taskId = :taskId",
            values={"phase": phase.value, "taskId": task_id},
        )

    async def save_title_options(self, task_id: str, title_options: List[TitleOption]):
        """保存标题方案列表"""
        await self.db.execute(
            query="UPDATE article SET titleOptions = :titleOptions WHERE taskId = :taskId",
            values={
                "taskId": task_id,
                "titleOptions": json.dumps(
                    [item.model_dump(by_alias=True) for item in title_options],
                    ensure_ascii=False,
                ),
            },
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
            query="""
                UPDATE article
                SET mainTitle = :mainTitle,
                    subTitle = :subTitle,
                    userDescription = :userDescription,
                    phase = :phase
                WHERE taskId = :taskId
            """,
            values={
                "taskId": task_id,
                "mainTitle": selected_main_title,
                "subTitle": selected_sub_title,
                "userDescription": user_description,
                "phase": ArticlePhaseEnum.OUTLINE_GENERATING.value,
            },
        )

    async def save_outline(self, task_id: str, outline: List[OutlineSection]):
        """保存大纲内容（不推进阶段）"""
        await self.db.execute(
            query="UPDATE article SET outline = :outline WHERE taskId = :taskId",
            values={
                "taskId": task_id,
                "outline": json.dumps([item.model_dump() for item in outline], ensure_ascii=False),
            },
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
            query="""
                UPDATE article
                SET outline = :outline,
                    phase = :phase
                WHERE taskId = :taskId
            """,
            values={
                "taskId": task_id,
                "outline": json.dumps([item.model_dump() for item in outline], ensure_ascii=False),
                "phase": ArticlePhaseEnum.CONTENT_GENERATING.value,
            },
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

        from app.services.article_agent_service import ArticleAgentService
        agent_service = ArticleAgentService()
        modified_outline = await agent_service.ai_modify_outline(
            main_title=article["mainTitle"],
            sub_title=article["subTitle"],
            current_outline=current_outline,
            modify_suggestion=modify_suggestion,
        )
        await self.db.execute(
            query="UPDATE article SET outline = :outline WHERE taskId = :taskId",
            values={
                "taskId": task_id,
                "outline": json.dumps(
                    [item.model_dump() for item in modified_outline],
                    ensure_ascii=False,
                ),
            },
        )
        return modified_outline

    async def update_article_status(
        self,
        task_id: str,
        status: ArticleStatusEnum,
        error_message: Optional[str] = None,
    ):
        if status == ArticleStatusEnum.COMPLETED:
            await self.db.execute(
                query="UPDATE article SET status = :status, completedTime = :completedTime WHERE taskId = :taskId",
                values={"status": status.value, "completedTime": datetime.now(), "taskId": task_id},
            )
        elif status == ArticleStatusEnum.FAILED:
            await self.db.execute(
                query="UPDATE article SET status = :status, errorMessage = :errorMessage WHERE taskId = :taskId",
                values={"status": status.value, "errorMessage": error_message, "taskId": task_id},
            )
        else:
            await self.db.execute(
                query="UPDATE article SET status = :status WHERE taskId = :taskId",
                values={"status": status.value, "taskId": task_id},
            )

    async def save_article_content(self, task_id: str, state: ArticleState):
        """将智能体生成结果持久化"""
        cover_image = None
        if state.images:
            cover = next((img for img in state.images if img.position == 1), None)
            if cover:
                cover_image = cover.url

        await self.db.execute(
            query="""
                UPDATE article
                SET mainTitle = :mainTitle, subTitle = :subTitle,
                    outline = :outline, content = :content,
                    fullContent = :fullContent, coverImage = :coverImage,
                    images = :images
                WHERE taskId = :taskId
            """,
            values={
                "mainTitle": state.title.main_title,
                "subTitle": state.title.sub_title,
                "outline": json.dumps(
                    [s.model_dump() for s in state.outline.sections], ensure_ascii=False
                ),
                "content": state.content,
                "fullContent": state.full_content,
                "coverImage": cover_image,
                "images": json.dumps(
                    [img.model_dump(by_alias=True) for img in state.images],
                    ensure_ascii=False,
                ),
                "taskId": task_id,
            },
        )

    async def get_article_detail(self, task_id: str, login_user: LoginUserVO) -> ArticleVO:
        row = await self.db.fetch_one(
            query="SELECT * FROM article WHERE taskId = :taskId AND isDelete = 0",
            values={"taskId": task_id},
        )
        throw_if_not(row, ErrorCode.NOT_FOUND_ERROR, "文章不存在")
        throw_if(
            row["userId"] != login_user.id and login_user.user_role != "admin",
            ErrorCode.NO_AUTH_ERROR,
            "无权限访问该文章",
        )
        return self._row_to_vo(row)

    async def list_article_by_page(
        self, request: ArticleQueryRequest, login_user: LoginUserVO
    ) -> Tuple[List[ArticleVO], int]:
        conditions = ["isDelete = 0"]
        values = {}

        if login_user.user_role != "admin":
            conditions.append("userId = :userId")
            values["userId"] = login_user.id
        elif request.user_id:
            conditions.append("userId = :userId")
            values["userId"] = request.user_id

        if request.status:
            conditions.append("status = :status")
            values["status"] = request.status

        if request.topic:
            conditions.append("topic LIKE :topic")
            values["topic"] = f"%{request.topic}%"

        where = " AND ".join(conditions)
        total = await self.db.fetch_val(f"SELECT COUNT(*) FROM article WHERE {where}", values=values)

        offset = (request.current - 1) * request.page_size
        values["limit"] = request.page_size
        values["offset"] = offset
        rows = await self.db.fetch_all(
            f"SELECT * FROM article WHERE {where} ORDER BY createTime DESC LIMIT :limit OFFSET :offset",
            values=values,
        )
        return [self._row_to_vo(r) for r in rows], total

    async def delete_article(self, article_id: int, login_user: LoginUserVO) -> bool:
        row = await self.db.fetch_one(
            query="SELECT * FROM article WHERE id = :id AND isDelete = 0",
            values={"id": article_id},
        )
        throw_if_not(row, ErrorCode.NOT_FOUND_ERROR, "文章不存在")
        throw_if(
            row["userId"] != login_user.id and login_user.user_role != "admin",
            ErrorCode.NO_AUTH_ERROR,
            "无权限删除该文章",
        )
        await self.db.execute(
            query="UPDATE article SET isDelete = 1 WHERE id = :id",
            values={"id": article_id},
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
