import asyncio

from databases import Database
from fastapi import APIRouter, Depends

from app.constants.user import UserConstant
from app.database import get_db
from app.deps import require_login
from app.exceptions import ErrorCode, throw_if
from app.schemas.article import (
    ArticleAiModifyOutlineRequest,
    ArticleConfirmOutlineRequest,
    ArticleConfirmTitleRequest,
    ArticleCreateRequest,
    ArticleQueryRequest,
    ArticleVO,
)
from app.schemas.common import BaseResponse, DeleteRequest
from app.schemas.user import LoginUserVO
from app.services.article.article_async_service import article_async_service
from app.services.article.article_service import ArticleService
from app.schemas.statistics import AgentExecutionStatsVO
from app.services.analytics.agent_log_service import AgentLogService

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
    task_id = await service.create_article_task_with_quota_check(
        request.topic,
        current_user,
        style,
        request.enabled_image_methods,
    )
    asyncio.create_task(
        article_async_service.execute_phase1(task_id, request.topic, style)
    )
    return BaseResponse.success(data=task_id, message="任务创建成功")


@router.post("/confirm-title", response_model=BaseResponse[None])
async def confirm_title(
    request: ArticleConfirmTitleRequest,
    db: Database = Depends(get_db),
    current_user: LoginUserVO = Depends(require_login),
):
    """确认标题并输入补充描述，触发阶段2大纲生成"""
    service = ArticleService(db)
    await service.confirm_title(
        task_id=request.task_id,
        selected_main_title=request.selected_main_title,
        selected_sub_title=request.selected_sub_title,
        user_description=request.user_description,
        login_user=current_user,
    )
    asyncio.create_task(article_async_service.execute_phase2(request.task_id))
    return BaseResponse.success(data=None)


@router.post("/confirm-outline", response_model=BaseResponse[None])
async def confirm_outline(
    request: ArticleConfirmOutlineRequest,
    db: Database = Depends(get_db),
    current_user: LoginUserVO = Depends(require_login),
):
    """确认大纲，触发阶段3正文生成"""
    service = ArticleService(db)
    await service.confirm_outline(
        task_id=request.task_id,
        outline=request.outline,
        login_user=current_user,
    )
    asyncio.create_task(article_async_service.execute_phase3(request.task_id))
    return BaseResponse.success(data=None)


@router.post("/ai-modify-outline", response_model=BaseResponse[list])
async def ai_modify_outline(
    request: ArticleAiModifyOutlineRequest,
    db: Database = Depends(get_db),
    current_user: LoginUserVO = Depends(require_login),
):
    """AI 修改大纲（VIP 专属功能）"""
    throw_if(
        current_user.user_role not in (UserConstant.VIP_ROLE, UserConstant.ADMIN_ROLE),
        ErrorCode.NO_AUTH_ERROR,
        "AI 修改大纲为 VIP 专属功能",
    )
    service = ArticleService(db)
    modified_outline = await service.ai_modify_outline(
        task_id=request.task_id,
        modify_suggestion=request.modify_suggestion,
        login_user=current_user,
    )
    return BaseResponse.success(data=[s.model_dump() for s in modified_outline])


@router.get("/progress/{task_id}")
async def get_progress(
    task_id: str,
    db: Database = Depends(get_db),
    current_user: LoginUserVO = Depends(require_login),
):
    throw_if(not task_id or not task_id.strip(), ErrorCode.PARAMS_ERROR, "任务ID不能为空")
    service = ArticleService(db)
    article_vo = await service.get_article_detail(task_id, current_user)
    from app.managers.sse_manager import sse_emitter_manager
    response = sse_emitter_manager.create_emitter(task_id)
    # 建立新队列后立即推送恢复数据，前端重连可从当前阶段续流
    article_async_service.push_recovery_state(task_id, article_vo)
    return response


@router.get("/execution-logs/{task_id}", response_model=BaseResponse[AgentExecutionStatsVO])
async def get_execution_logs(
    task_id: str,
    db: Database = Depends(get_db),
):
    """获取任务的智能体执行日志（taskId 本身即为随机字符串，无需额外鉴权）"""
    throw_if(not task_id or not task_id.strip(), ErrorCode.PARAMS_ERROR, "任务ID不能为空")
    service = AgentLogService(db)
    stats = await service.get_execution_stats(task_id)
    return BaseResponse.success(data=stats)


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
