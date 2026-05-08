from typing import List, Tuple
from sqlalchemy import select, func, and_

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

    async def register(self, request: UserRegisterRequest) -> int:
        throw_if(len(request.user_account) < 4, ErrorCode.PARAMS_ERROR, "账号长度不能小于 4 位")
        throw_if(len(request.user_password) < 8, ErrorCode.PARAMS_ERROR, "密码长度不能小于 8 位")
        throw_if(request.user_password != request.check_password, ErrorCode.PARAMS_ERROR, "两次输入的密码不一致")

        query = select(func.count(User.id)).where(
            and_(User.user_account == request.user_account, User.is_delete == 0)
        )
        count = await self.db.fetch_val(query)
        throw_if(count > 0, ErrorCode.USER_ALREADY_EXIST, "账号已存在")

        user_id = await self.db.execute(
            query="""
                INSERT INTO user (userAccount, userPassword, userName, userRole)
                VALUES (:userAccount, :userPassword, :userName, :userRole)
            """,
            values={
                "userAccount": request.user_account,
                "userPassword": encrypt_password(request.user_password),
                "userName": f"用户{request.user_account}",
                "userRole": "user",
            },
        )
        return user_id

    async def login(self, request: UserLoginRequest) -> LoginUserVO:
        throw_if(len(request.user_account) < 4, ErrorCode.PARAMS_ERROR, "账号长度不能小于 4 位")
        throw_if(len(request.user_password) < 8, ErrorCode.PARAMS_ERROR, "密码长度不能小于 8 位")

        query = select(User).where(
            and_(User.user_account == request.user_account, User.is_delete == 0)
        )
        user = await self.db.fetch_one(query)
        throw_if_not(user, ErrorCode.USER_NOT_EXIST, "用户不存在")
        throw_if(
            user["userPassword"] != encrypt_password(request.user_password),
            ErrorCode.PASSWORD_ERROR,
            "密码错误",
        )

        return LoginUserVO(
            id=user["id"],
            userAccount=user["userAccount"],
            userName=user["userName"],
            userAvatar=user["userAvatar"],
            userProfile=user["userProfile"],
            userRole=user["userRole"],
            createTime=user["createTime"].isoformat(),
            updateTime=user["updateTime"].isoformat(),
        )

    async def get_by_id(self, user_id: int) -> UserVO:
        query = select(User).where(and_(User.id == user_id, User.is_delete == 0))
        user = await self.db.fetch_one(query)
        throw_if_not(user, ErrorCode.USER_NOT_EXIST)
        return UserVO(
            id=user["id"],
            userAccount=user["userAccount"],
            userName=user["userName"],
            userAvatar=user["userAvatar"],
            userProfile=user["userProfile"],
            userRole=user["userRole"],
            createTime=user["createTime"].isoformat(),
        )

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

        count_query = select(func.count(User.id)).where(and_(*conditions))
        total = await self.db.fetch_val(count_query)

        offset = (request.current - 1) * request.page_size
        data_query = (
            select(User).where(and_(*conditions)).offset(offset).limit(request.page_size)
        )
        rows = await self.db.fetch_all(data_query)

        users = [
            UserVO(
                id=r["id"],
                userAccount=r["userAccount"],
                userName=r["userName"],
                userAvatar=r["userAvatar"],
                userProfile=r["userProfile"],
                userRole=r["userRole"],
                createTime=r["createTime"].isoformat(),
            )
            for r in rows
        ]
        return users, total

    async def add_user(self, request: UserAddRequest) -> int:
        return await self.db.execute(
            query="""
                INSERT INTO user (userAccount, userPassword, userName, userAvatar, userProfile, userRole)
                VALUES (:userAccount, :userPassword, :userName, :userAvatar, :userProfile, :userRole)
            """,
            values={
                "userAccount": request.user_account,
                "userPassword": encrypt_password(request.user_password),
                "userName": request.user_name,
                "userAvatar": request.user_avatar,
                "userProfile": request.user_profile,
                "userRole": request.user_role,
            },
        )

    async def update_user(self, request: UserUpdateRequest) -> bool:
        fields, values = [], {"id": request.id}
        if request.user_name is not None:
            fields.append("userName = :userName")
            values["userName"] = request.user_name
        if request.user_avatar is not None:
            fields.append("userAvatar = :userAvatar")
            values["userAvatar"] = request.user_avatar
        if request.user_profile is not None:
            fields.append("userProfile = :userProfile")
            values["userProfile"] = request.user_profile
        if request.user_role is not None:
            fields.append("userRole = :userRole")
            values["userRole"] = request.user_role

        throw_if(not fields, ErrorCode.PARAMS_ERROR, "没有可更新的字段")
        await self.db.execute(
            query=f"UPDATE user SET {', '.join(fields)} WHERE id = :id AND isDelete = 0",
            values=values,
        )
        return True

    async def delete_user(self, user_id: int) -> bool:
        await self.db.execute(
            query="UPDATE user SET isDelete = 1 WHERE id = :id",
            values={"id": user_id},
        )
        return True
