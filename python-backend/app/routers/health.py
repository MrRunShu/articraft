from fastapi import APIRouter
from app.schemas.common import BaseResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=BaseResponse[str])
async def health_check():
    return BaseResponse.success(data="ok", message="服务正常")
