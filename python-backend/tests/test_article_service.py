"""
DB 集成测试：ArticleService CRUD
需要 MySQL 连接，运行前确保本地 MySQL 已启动且 .env 配置正确
"""
import pytest
import pytest_asyncio
from app.database import database
from app.models.enums import ArticleStatusEnum
from app.schemas.article import ArticleState, TitleResult, OutlineResult, OutlineSection, ImageResult
from app.schemas.user import LoginUserVO
from app.services.article.article_service import ArticleService


# ---- fixtures ----

@pytest_asyncio.fixture(autouse=True)
async def db_connection():
    await database.connect()
    yield
    await database.disconnect()


@pytest.fixture
def service():
    return ArticleService(database)


@pytest.fixture
def mock_user():
    return LoginUserVO(
        id=1,
        userAccount="test_user",
        userName="测试用户",
        userAvatar=None,
        userProfile=None,
        userRole="user",
        createTime="2026-01-01T00:00:00",
        updateTime="2026-01-01T00:00:00",
    )


@pytest.fixture
def admin_user():
    return LoginUserVO(
        id=999,
        userAccount="admin",
        userName="管理员",
        userAvatar=None,
        userProfile=None,
        userRole="admin",
        createTime="2026-01-01T00:00:00",
        updateTime="2026-01-01T00:00:00",
    )


def make_article_state(task_id: str) -> ArticleState:
    state = ArticleState()
    state.task_id = task_id
    state.topic = "测试选题"
    state.title = TitleResult(mainTitle="测试主标题", subTitle="测试副标题")
    state.outline = OutlineResult(sections=[
        OutlineSection(section=1, title="第一章", points=["要点1", "要点2"]),
        OutlineSection(section=2, title="第二章", points=["要点3"]),
    ])
    state.content = "## 第一章\n内容一\n## 第二章\n内容二"
    state.full_content = "## 第一章\n内容一\n![第一章](http://img1.jpg)\n## 第二章\n内容二"
    state.images = [
        ImageResult(position=1, url="http://cover.jpg", method="PICSUM",
                    keywords="cover", sectionTitle="", description="封面"),
        ImageResult(position=2, url="http://img1.jpg", method="PICSUM",
                    keywords="city", sectionTitle="第一章", description="第一章配图"),
    ]
    return state


# ---- tests ----

@pytest.mark.asyncio
async def test_create_article_task(service, mock_user):
    """创建任务，返回 UUID 格式的 taskId"""
    task_id = await service.create_article_task_with_quota_check("大城市低成本生活", mock_user)

    assert task_id and len(task_id) == 36  # UUID 格式
    # 验证写入 DB
    row = await database.fetch_one(
        "SELECT * FROM article WHERE taskId = :taskId AND isDelete = 0",
        values={"taskId": task_id},
    )
    assert row is not None
    assert row["status"] == ArticleStatusEnum.PENDING.value
    assert row["userId"] == mock_user.id

    # 清理
    await database.execute("DELETE FROM article WHERE taskId = :taskId", values={"taskId": task_id})


@pytest.mark.asyncio
async def test_update_article_status(service, mock_user):
    """状态流转：PENDING → PROCESSING → COMPLETED / FAILED"""
    task_id = await service.create_article_task_with_quota_check("状态测试", mock_user)

    await service.update_article_status(task_id, ArticleStatusEnum.PROCESSING)
    row = await database.fetch_one("SELECT status FROM article WHERE taskId = :t", values={"t": task_id})
    assert row["status"] == "PROCESSING"

    await service.update_article_status(task_id, ArticleStatusEnum.COMPLETED)
    row = await database.fetch_one("SELECT status, completedTime FROM article WHERE taskId = :t", values={"t": task_id})
    assert row["status"] == "COMPLETED"
    assert row["completedTime"] is not None

    await database.execute("DELETE FROM article WHERE taskId = :taskId", values={"taskId": task_id})


@pytest.mark.asyncio
async def test_update_article_status_failed(service, mock_user):
    """状态流转到 FAILED，errorMessage 写入"""
    task_id = await service.create_article_task_with_quota_check("失败测试", mock_user)
    await service.update_article_status(task_id, ArticleStatusEnum.FAILED, "大模型调用超时")

    row = await database.fetch_one("SELECT status, errorMessage FROM article WHERE taskId = :t", values={"t": task_id})
    assert row["status"] == "FAILED"
    assert row["errorMessage"] == "大模型调用超时"

    await database.execute("DELETE FROM article WHERE taskId = :taskId", values={"taskId": task_id})


@pytest.mark.asyncio
async def test_save_article_content(service, mock_user):
    """持久化智能体生成结果"""
    task_id = await service.create_article_task_with_quota_check("内容持久化测试", mock_user)
    state = make_article_state(task_id)

    await service.save_article_content(task_id, state)

    row = await database.fetch_one("SELECT * FROM article WHERE taskId = :t", values={"t": task_id})
    assert row["mainTitle"] == "测试主标题"
    assert row["subTitle"] == "测试副标题"
    assert row["content"] is not None
    assert row["fullContent"] is not None
    assert row["coverImage"] == "http://cover.jpg"
    assert row["images"] is not None

    await database.execute("DELETE FROM article WHERE taskId = :taskId", values={"taskId": task_id})


@pytest.mark.asyncio
async def test_get_article_detail(service, mock_user):
    """获取文章详情 + 权限校验"""
    from app.exceptions import BusinessException

    task_id = await service.create_article_task_with_quota_check("详情测试", mock_user)

    # 同一用户可以访问
    vo = await service.get_article_detail(task_id, mock_user)
    assert vo.task_id == task_id
    assert vo.status == "PENDING"

    # 其他普通用户无权访问
    other_user = LoginUserVO(
        id=2, userAccount="other", userName="其他用户", userAvatar=None,
        userProfile=None, userRole="user",
        createTime="2026-01-01T00:00:00", updateTime="2026-01-01T00:00:00",
    )
    with pytest.raises(BusinessException):
        await service.get_article_detail(task_id, other_user)

    await database.execute("DELETE FROM article WHERE taskId = :taskId", values={"taskId": task_id})


@pytest.mark.asyncio
async def test_get_article_detail_admin_can_access_any(service, mock_user, admin_user):
    """管理员可以访问任意用户的文章"""
    task_id = await service.create_article_task_with_quota_check("管理员访问测试", mock_user)

    vo = await service.get_article_detail(task_id, admin_user)
    assert vo.task_id == task_id

    await database.execute("DELETE FROM article WHERE taskId = :taskId", values={"taskId": task_id})


@pytest.mark.asyncio
async def test_list_article_by_page(service, mock_user):
    """分页查询：普通用户只能看自己的文章"""
    from app.schemas.article import ArticleQueryRequest

    task_id1 = await service.create_article_task_with_quota_check("分页测试1", mock_user)
    task_id2 = await service.create_article_task_with_quota_check("分页测试2", mock_user)

    request = ArticleQueryRequest(current=1, pageSize=10)
    articles, total = await service.list_article_by_page(request, mock_user)

    task_ids = [a.task_id for a in articles]
    assert task_id1 in task_ids
    assert task_id2 in task_ids
    assert total >= 2

    await database.execute("DELETE FROM article WHERE taskId IN (:t1, :t2)", values={"t1": task_id1, "t2": task_id2})


@pytest.mark.asyncio
async def test_delete_article(service, mock_user):
    """软删除：isDelete=1，其他用户无权删除"""
    from app.exceptions import BusinessException

    task_id = await service.create_article_task_with_quota_check("删除测试", mock_user)
    row = await database.fetch_one("SELECT id FROM article WHERE taskId = :t", values={"t": task_id})
    article_id = row["id"]

    # 他人无权删除
    other_user = LoginUserVO(
        id=2, userAccount="other", userName="其他用户", userAvatar=None,
        userProfile=None, userRole="user",
        createTime="2026-01-01T00:00:00", updateTime="2026-01-01T00:00:00",
    )
    with pytest.raises(BusinessException):
        await service.delete_article(article_id, other_user)

    # 本人可以删除
    result = await service.delete_article(article_id, mock_user)
    assert result is True

    row = await database.fetch_one("SELECT isDelete FROM article WHERE id = :id", values={"id": article_id})
    assert row["isDelete"] == 1
