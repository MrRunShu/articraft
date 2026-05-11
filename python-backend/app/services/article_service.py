import json
import logging
import uuid
from datetime import datetime
from typing import List, Optional, Tuple

from app.database import database
from app.exceptions import ErrorCode, throw_if, throw_if_not
from app.models.enums import ArticleStatusEnum
from app.schemas.article import ArticleQueryRequest, ArticleState, ArticleVO
from app.schemas.user import LoginUserVO

logger = logging.getLogger(__name__)


class ArticleService:
    def __init__(self, db=None):
        self.db = db or database

    async def create_article_task_with_quota_check(
        self, topic: str, login_user: LoginUserVO
    ) -> str:
        """创建文章任务，返回 taskId（配额检查第7期实现）"""
        task_id = str(uuid.uuid4())
        await self.db.execute(
            query="""
                INSERT INTO article (taskId, userId, topic, status, createTime)
                VALUES (:taskId, :userId, :topic, :status, :createTime)
            """,
            values={
                "taskId": task_id,
                "userId": login_user.id,
                "topic": topic,
                "status": ArticleStatusEnum.PENDING.value,
                "createTime": datetime.now(),
            },
        )
        return task_id

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
        return ArticleVO(
            id=row["id"],
            taskId=row["taskId"],
            userId=row["userId"],
            topic=row["topic"],
            mainTitle=row["mainTitle"],
            subTitle=row["subTitle"],
            outline=json.loads(row["outline"]) if row["outline"] else None,
            content=row["content"],
            fullContent=row["fullContent"],
            coverImage=row["coverImage"],
            images=json.loads(row["images"]) if row["images"] else None,
            status=row["status"],
            errorMessage=row["errorMessage"],
            createTime=row["createTime"].isoformat(),
            completedTime=row["completedTime"].isoformat() if row["completedTime"] else None,
        )
