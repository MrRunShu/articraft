import uuid
from typing import Optional
from fastapi import Cookie, Depends

from app.constants.user import UserConstant
from app.exceptions import ErrorCode, BusinessException
from app.schemas.user import LoginUserVO
from app.utils.session import get_session


async def get_session_id(session_id: Optional[str] = Cookie(None, alias="SESSION")) -> Optional[str]:
    return session_id


async def get_current_user(
    session_id: Optional[str] = Depends(get_session_id),
) -> Optional[LoginUserVO]:
    if not session_id:
        return None
    session_data = await get_session(session_id)
    if not session_data or "user" not in session_data:
        return None
    return LoginUserVO(**session_data["user"])


async def require_login(
    current_user: Optional[LoginUserVO] = Depends(get_current_user),
) -> LoginUserVO:
    if not current_user:
        raise BusinessException(ErrorCode.NOT_LOGIN_ERROR)
    return current_user


async def require_admin(
    current_user: LoginUserVO = Depends(require_login),
) -> LoginUserVO:
    if current_user.user_role != UserConstant.ADMIN_ROLE:
        raise BusinessException(ErrorCode.NO_AUTH_ERROR)
    return current_user


def generate_session_id() -> str:
    return str(uuid.uuid4())
