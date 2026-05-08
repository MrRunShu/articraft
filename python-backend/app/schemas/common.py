from typing import TypeVar, Generic, Optional
from pydantic import BaseModel, Field

T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    code: int = Field(default=0)
    data: Optional[T] = Field(default=None)
    message: str = Field(default="ok")

    @classmethod
    def success(cls, data: Optional[T] = None, message: str = "ok") -> "BaseResponse[T]":
        return cls(code=0, data=data, message=message)

    @classmethod
    def error(cls, code: int, message: str) -> "BaseResponse[T]":
        return cls(code=code, data=None, message=message)


class PageRequest(BaseModel):
    current: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100, alias="pageSize")
    sort_field: Optional[str] = Field(default=None, alias="sortField")
    sort_order: Optional[str] = Field(default="descend", alias="sortOrder")


class DeleteRequest(BaseModel):
    id: int
