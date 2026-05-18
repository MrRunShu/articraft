from typing import Optional
from pydantic import BaseModel, Field

from app.schemas.common import PageRequest


class UserRegisterRequest(BaseModel):
    user_account: str = Field(..., min_length=4, max_length=256, alias="userAccount")
    user_password: str = Field(..., min_length=8, max_length=512, alias="userPassword")
    check_password: str = Field(..., min_length=8, max_length=512, alias="checkPassword")


class UserLoginRequest(BaseModel):
    user_account: str = Field(..., min_length=4, max_length=256, alias="userAccount")
    user_password: str = Field(..., min_length=8, max_length=512, alias="userPassword")


class UserAddRequest(BaseModel):
    user_account: str = Field(..., alias="userAccount")
    user_password: str = Field(..., alias="userPassword")
    user_name: Optional[str] = Field(None, alias="userName")
    user_avatar: Optional[str] = Field(None, alias="userAvatar")
    user_profile: Optional[str] = Field(None, alias="userProfile")
    user_role: str = Field(default="user", alias="userRole")


class UserUpdateRequest(BaseModel):
    id: int
    user_name: Optional[str] = Field(None, alias="userName")
    user_avatar: Optional[str] = Field(None, alias="userAvatar")
    user_profile: Optional[str] = Field(None, alias="userProfile")
    user_role: Optional[str] = Field(None, alias="userRole")


class UserQueryRequest(PageRequest):
    id: Optional[int] = None
    user_account: Optional[str] = Field(None, alias="userAccount")
    user_name: Optional[str] = Field(None, alias="userName")
    user_profile: Optional[str] = Field(None, alias="userProfile")
    user_role: Optional[str] = Field(None, alias="userRole")


class UserVO(BaseModel):
    id: int
    user_account: str = Field(..., alias="userAccount")
    user_name: Optional[str] = Field(None, alias="userName")
    user_avatar: Optional[str] = Field(None, alias="userAvatar")
    user_profile: Optional[str] = Field(None, alias="userProfile")
    user_role: str = Field(..., alias="userRole")
    vip_time: Optional[str] = Field(None, alias="vipTime")
    create_time: str = Field(..., alias="createTime")

    class Config:
        populate_by_name = True


class LoginUserVO(BaseModel):
    id: int
    user_account: str = Field(..., alias="userAccount")
    user_name: Optional[str] = Field(None, alias="userName")
    user_avatar: Optional[str] = Field(None, alias="userAvatar")
    user_profile: Optional[str] = Field(None, alias="userProfile")
    user_role: str = Field(..., alias="userRole")
    vip_time: Optional[str] = Field(None, alias="vipTime")
    create_time: str = Field(..., alias="createTime")
    update_time: str = Field(..., alias="updateTime")

    class Config:
        populate_by_name = True
