import asyncio

from databases import Database
from fastapi import APIRouter, Depends

from app.database import get_db
from app.deps import require_login
from app.exceptions import ErrorCode, throw_if
from app.schemas.article import ArticleCreateRequest, ArticleQueryRequest, ArticleVO
from app.schemas.common import BaseResponse, DeleteRequest
from app.schemas.user import LoginUserVO
from app.services.article_async_service import article_async_service
from app.services.article_service import ArticleService

router = APIRouter(prefix="/article", tags=["文章管理"])


@router.post("/create", response_model=BaseResponse[str])
async def create_article(
    request: ArticleCreateRequest,
    db: Database = Depends(get_db),
    current_user: LoginUserVO = Depends(require_login),
):
    throw_if(not request.topic or not request.topic.strip(), ErrorCode.PARAMS_ERROR, "选题不能为空")
    service = ArticleService(db)
    style = request.style or "POPULAR"
    task_id = await service.create_article_task_with_quota_check(request.topic, current_user, style)
    asyncio.create_task(article_async_service.execute_article_generation(task_id, request.topic, style))
    return BaseResponse.success(data=task_id, message="任务创建成功")


@router.get("/progress/{task_id}")
async def get_progress(
    task_id: str,
    db: Database = Depends(get_db),
    current_user: LoginUserVO = Depends(require_login),
):
    throw_if(not task_id or not task_id.strip(), ErrorCode.PARAMS_ERROR, "任务ID不能为空")
    service = ArticleService(db)
    await service.get_article_detail(task_id, current_user)
    from app.managers.sse_manager import sse_emitter_manager
    return sse_emitter_manager.create_emitter(task_id)


@router.get("/{task_id}", response_model=BaseResponse[ArticleVO])
async def get_article(
    task_id: str,
    db: Database = Depends(get_db),
    current_user: LoginUserVO = Depends(require_login),
):
    service = ArticleService(db)
    article_vo = await service.get_article_detail(task_id, current_user)
    return BaseResponse.success(data=article_vo)


@router.post("/list", response_model=BaseResponse[dict])
async def list_article(
    request: ArticleQueryRequest,
    db: Database = Depends(get_db),
    current_user: LoginUserVO = Depends(require_login),
):
    service = ArticleService(db)
    articles, total = await service.list_article_by_page(request, current_user)
    return BaseResponse.success(data={
        "records": [a.model_dump(by_alias=True) for a in articles],
        "total": total,
        "current": request.current,
        "size": request.page_size,
    })


@router.post("/delete", response_model=BaseResponse[bool])
async def delete_article(
    request: DeleteRequest,
    db: Database = Depends(get_db),
    current_user: LoginUserVO = Depends(require_login),
):
    throw_if(not request.id, ErrorCode.PARAMS_ERROR, "文章ID不能为空")
    service = ArticleService(db)
    result = await service.delete_article(request.id, current_user)
    return BaseResponse.success(data=result, message="删除成功")
