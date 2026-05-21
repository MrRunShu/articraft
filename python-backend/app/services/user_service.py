from typing import List, Tuple
from sqlalchemy import select, func, and_, insert, update

from app.constants.user import UserConstant
from app.database import database
from app.exceptions import ErrorCode, throw_if, throw_if_not
from app.models.user import User
from app.schemas.user import (
    UserRegisterRequest,
    UserLoginRequest,
    UserAddRequest,
    UserUpdateRequest,
    UserQueryRequest,
    LoginUserVO,
    UserVO,
)
from app.utils.password import encrypt_password, verify_password


class UserService:
    def __init__(self, db=None):
        self.db = db or database

    # ─── VO 映射 ─────────────────────────────────────────────────────────────

    @staticmethod
    def _row_to_login_user_vo(row) -> LoginUserVO:
        return LoginUserVO(
            id=row["id"],
            userAccount=row["userAccount"],
            userName=row["userName"],
            userAvatar=row["userAvatar"],
            userProfile=row["userProfile"],
            userRole=row["userRole"],
            vipTime=row["vipTime"].isoformat() if row["vipTime"] else None,
            createTime=row["createTime"].isoformat(),
            updateTime=row["updateTime"].isoformat(),
        )

    @staticmethod
    def _row_to_user_vo(row) -> UserVO:
        return UserVO(
            id=row["id"],
            userAccount=row["userAccount"],
            userName=row["userName"],
            userAvatar=row["userAvatar"],
            userProfile=row["userProfile"],
            userRole=row["userRole"],
            vipTime=row["vipTime"].isoformat() if row["vipTime"] else None,
            createTime=row["createTime"].isoformat(),
        )

    # ─── 业务方法 ─────────────────────────────────────────────────────────────

    async def register(self, request: UserRegisterRequest) -> int:
        throw_if(len(request.user_account) < 4, ErrorCode.PARAMS_ERROR, "账号长度不能小于 4 位")
        throw_if(len(request.user_password) < 8, ErrorCode.PARAMS_ERROR, "密码长度不能小于 8 位")
        throw_if(request.user_password != request.check_password, ErrorCode.PARAMS_ERROR, "两次输入的密码不一致")

        count = await self.db.fetch_val(
            select(func.count(User.id)).where(
                and_(User.user_account == request.user_account, User.is_delete == 0)
            )
        )
        throw_if(count > 0, ErrorCode.USER_ALREADY_EXIST, "账号已存在")

        user_id = await self.db.execute(
            insert(User).values(
                user_account=request.user_account,
                user_password=encrypt_password(request.user_password),
                user_name=f"用户{request.user_account}",
                user_role=UserConstant.DEFAULT_ROLE,
            )
        )
        return user_id

    async def login(self, request: UserLoginRequest) -> LoginUserVO:
        throw_if(len(request.user_account) < 4, ErrorCode.PARAMS_ERROR, "账号长度不能小于 4 位")
        throw_if(len(request.user_password) < 8, ErrorCode.PARAMS_ERROR, "密码长度不能小于 8 位")

        user = await self.db.fetch_one(
            select(User).where(
                and_(User.user_account == request.user_account, User.is_delete == 0)
            )
        )
        throw_if_not(user, ErrorCode.USER_NOT_EXIST, "用户不存在")
        throw_if(
            user["userPassword"] != encrypt_password(request.user_password),
            ErrorCode.PASSWORD_ERROR,
            "密码错误",
        )
        return self._row_to_login_user_vo(user)

    async def get_by_id(self, user_id: int) -> UserVO:
        user = await self.db.fetch_one(
            select(User).where(and_(User.id == user_id, User.is_delete == 0))
        )
        throw_if_not(user, ErrorCode.USER_NOT_EXIST)
        return self._row_to_user_vo(user)

    async def list_by_page(self, request: UserQueryRequest) -> Tuple[List[UserVO], int]:
        conditions = [User.is_delete == 0]
        if request.id:
            conditions.append(User.id == request.id)
        if request.user_account:
            conditions.append(User.user_account.like(f"%{request.user_account}%"))
        if request.user_name:
            conditions.append(User.user_name.like(f"%{request.user_name}%"))
        if request.user_role:
            conditions.append(User.user_role == request.user_role)

        total = await self.db.fetch_val(
            select(func.count(User.id)).where(and_(*conditions))
        )
        offset = (request.current - 1) * request.page_size
        rows = await self.db.fetch_all(
            select(User).where(and_(*conditions)).offset(offset).limit(request.page_size)
        )
        return [self._row_to_user_vo(r) for r in rows], total

    async def add_user(self, request: UserAddRequest) -> int:
        return await self.db.execute(
            insert(User).values(
                user_account=request.user_account,
                user_password=encrypt_password(request.user_password),
                user_name=request.user_name,
                user_avatar=request.user_avatar,
                user_profile=request.user_profile,
                user_role=request.user_role,
            )
        )

    async def update_user(self, request: UserUpdateRequest) -> bool:
        update_values = {}
        if request.user_name is not None:
            update_values["user_name"] = request.user_name
        if request.user_avatar is not None:
            update_values["user_avatar"] = request.user_avatar
        if request.user_profile is not None:
            update_values["user_profile"] = request.user_profile
        if request.user_role is not None:
            update_values["user_role"] = request.user_role

        throw_if(not update_values, ErrorCode.PARAMS_ERROR, "没有可更新的字段")
        await self.db.execute(
            update(User)
            .where(and_(User.id == request.id, User.is_delete == 0))
            .values(**update_values)
        )
        return True

    async def delete_user(self, user_id: int) -> bool:
        await self.db.execute(
            update(User).where(User.id == user_id).values(is_delete=1)
        )
        return True
