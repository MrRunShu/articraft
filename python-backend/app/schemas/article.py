from typing import Optional, List, Any
from pydantic import BaseModel, Field

from app.schemas.common import PageRequest


class TitleResult(BaseModel):
    main_title: str = Field(..., alias="mainTitle")
    sub_title: str = Field(..., alias="subTitle")

    class Config:
        populate_by_name = True


class OutlineSection(BaseModel):
    section: int
    title: str
    points: List[str]


class OutlineResult(BaseModel):
    sections: List[OutlineSection]


class ImageRequirement(BaseModel):
    position: int
    type: str
    section_title: str = Field(..., alias="sectionTitle")
    keywords: str

    class Config:
        populate_by_name = True


class ImageResult(BaseModel):
    position: int
    url: str
    method: str
    keywords: str
    section_title: str = Field(..., alias="sectionTitle")
    description: str

    class Config:
        populate_by_name = True


class ArticleState:
    """智能体之间共享的状态容器（非Pydantic，仅内存传递）"""

    def __init__(self):
        self.task_id: Optional[str] = None
        self.topic: Optional[str] = None
        self.title: Optional[TitleResult] = None
        self.outline: Optional[OutlineResult] = None
        self.content: Optional[str] = None
        self.image_requirements: Optional[List[ImageRequirement]] = None
        self.images: Optional[List[ImageResult]] = None
        self.cover_image: Optional[str] = None
        self.full_content: Optional[str] = None


class ArticleCreateRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=500)


class ArticleQueryRequest(PageRequest):
    status: Optional[str] = None
    user_id: Optional[int] = Field(None, alias="userId")

    class Config:
        populate_by_name = True


class ArticleVO(BaseModel):
    id: int
    task_id: str = Field(..., alias="taskId")
    user_id: int = Field(..., alias="userId")
    topic: str
    main_title: Optional[str] = Field(None, alias="mainTitle")
    sub_title: Optional[str] = Field(None, alias="subTitle")
    outline: Optional[Any] = None
    content: Optional[str] = None
    full_content: Optional[str] = Field(None, alias="fullContent")
    cover_image: Optional[str] = Field(None, alias="coverImage")
    images: Optional[Any] = None
    status: str
    error_message: Optional[str] = Field(None, alias="errorMessage")
    create_time: str = Field(..., alias="createTime")
    completed_time: Optional[str] = Field(None, alias="completedTime")

    class Config:
        populate_by_name = True
