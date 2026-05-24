import json
import pytest
from app.services.article.article_agent_service import ArticleAgentService
from app.schemas.article import ArticleState


def make_agent_service():
    """创建 ArticleAgentService 实例但跳过 __init__（避免读取 config）"""
    from app.services.article.article_agent_service import ArticleAgentService
    svc = ArticleAgentService.__new__(ArticleAgentService)
    return svc


def make_image_result(position, section_title, url):
    from app.schemas.article import ImageResult
    return ImageResult(
        position=position,
        url=url,
        method="PICSUM",
        keywords="test",
        sectionTitle=section_title,
        description="test",
    )


# ---- _parse_json_response tests ----

def test_parse_json_response_plain():
    svc = make_agent_service()
    data = svc._parse_json_response('{"mainTitle": "标题", "subTitle": "副标题"}', "标题")
    assert data["mainTitle"] == "标题"
    assert data["subTitle"] == "副标题"


def test_parse_json_response_with_code_block():
    svc = make_agent_service()
    content = '```json\n{"mainTitle": "标题", "subTitle": "副标题"}\n```'
    data = svc._parse_json_response(content, "标题")
    assert data["mainTitle"] == "标题"


def test_parse_json_response_double_braces():
    svc = make_agent_service()
    content = '{{\n  "mainTitle": "标题",\n  "subTitle": "副标题"\n}}'
    data = svc._parse_json_response(content, "标题")
    assert data["mainTitle"] == "标题"


def test_parse_json_response_invalid_raises():
    svc = make_agent_service()
    with pytest.raises(RuntimeError, match="解析失败"):
        svc._parse_json_response("这不是JSON", "标题")


# ---- merge_images_into_content tests ----

def test_merge_images_inserts_after_section():
    svc = make_agent_service()
    from app.schemas.article import ArticleState
    state = ArticleState()
    state.content = "## 第一章\n内容一\n## 第二章\n内容二"
    state.images = [
        make_image_result(1, "", "http://cover.jpg"),
        make_image_result(2, "第一章", "http://img1.jpg"),
    ]
    svc.merge_images_into_content(state)
    assert "http://img1.jpg" in state.full_content
    assert "http://cover.jpg" not in state.full_content
    assert state.full_content.index("## 第一章") < state.full_content.index("http://img1.jpg")


def test_merge_images_no_images():
    svc = make_agent_service()
    from app.schemas.article import ArticleState
    state = ArticleState()
    state.content = "## 第一章\n内容"
    state.images = []
    svc.merge_images_into_content(state)
    assert state.full_content == state.content


# ---- 集成测试：真实调用 DeepSeek API ----

@pytest.mark.asyncio
async def test_agent1_generate_title_real_api():
    """智能体1：真实调用 DeepSeek，验证 API key 可用 + 标题结构正确"""
    svc = ArticleAgentService()
    state = ArticleState()
    state.topic = "年轻人如何在大城市低成本生活"

    await svc.agent1_generate_title(state)

    assert state.title is not None
    assert state.title.main_title and len(state.title.main_title) > 0
    assert state.title.sub_title and len(state.title.sub_title) > 0


@pytest.mark.asyncio
async def test_agent2_generate_outline_real_api():
    """智能体2：真实调用 DeepSeek，验证大纲流式输出 + 结构解析"""
    svc = ArticleAgentService()
    state = ArticleState()
    state.topic = "年轻人如何在大城市低成本生活"

    await svc.agent1_generate_title(state)

    chunks = []
    await svc.agent2_generate_outline(state, lambda msg: chunks.append(msg))

    assert state.outline is not None
    assert len(state.outline.sections) > 0
    assert len(chunks) > 0  # 流式有内容输出


@pytest.mark.asyncio
async def test_agent3_generate_content_real_api():
    """智能体3：真实调用 DeepSeek，验证正文流式输出"""
    svc = ArticleAgentService()
    state = ArticleState()
    state.topic = "年轻人如何在大城市低成本生活"

    await svc.agent1_generate_title(state)
    await svc.agent2_generate_outline(state, lambda msg: None)

    chunks = []
    await svc.agent3_generate_content(state, lambda msg: chunks.append(msg))

    assert state.content and len(state.content) > 100
    assert len(chunks) > 0
    assert "##" in state.content  # Markdown 章节标题


@pytest.mark.asyncio
async def test_agent4_analyze_image_requirements_real_api():
    """智能体4：真实调用 DeepSeek，验证配图需求解析"""
    svc = ArticleAgentService()
    state = ArticleState()
    state.topic = "年轻人如何在大城市低成本生活"

    await svc.agent1_generate_title(state)
    await svc.agent2_generate_outline(state, lambda msg: None)
    await svc.agent3_generate_content(state, lambda msg: None)
    await svc.agent4_analyze_image_requirements(state)

    assert state.image_requirements is not None
    assert len(state.image_requirements) > 0
    cover = next((r for r in state.image_requirements if r.position == 1), None)
    assert cover is not None  # 必须有封面图需求


@pytest.mark.asyncio
async def test_agent5_generate_images_real_api():
    """智能体5：Pexels/Picsum 图片搜索（验证降级策略）"""
    svc = ArticleAgentService()
    state = ArticleState()
    state.topic = "年轻人如何在大城市低成本生活"

    await svc.agent1_generate_title(state)
    await svc.agent2_generate_outline(state, lambda msg: None)
    await svc.agent3_generate_content(state, lambda msg: None)
    await svc.agent4_analyze_image_requirements(state)

    imgs = []
    await svc.agent5_generate_images(state, lambda msg: imgs.append(msg))

    assert state.images is not None
    assert len(state.images) == len(state.image_requirements)
    for img in state.images:
        assert img.url and img.url.startswith("http")  # 每张图都有 URL


@pytest.mark.asyncio
async def test_full_pipeline_real_api():
    """完整 5 智能体流程 end-to-end（耗时约 1~2 分钟）"""
    svc = ArticleAgentService()
    state = ArticleState()
    state.topic = "年轻人如何在大城市低成本生活"
    state.task_id = "test-pipeline-001"

    messages = []
    await svc.execute_article_generation(state, lambda msg: messages.append(msg))

    assert state.title is not None
    assert state.outline is not None and len(state.outline.sections) > 0
    assert state.content and len(state.content) > 200
    assert state.image_requirements is not None
    assert state.images is not None
    assert state.full_content and len(state.full_content) > 200
    # SSE 消息包含各阶段完成信号
    assert any("AGENT1_COMPLETE" in m for m in messages)
    assert any("AGENT3_STREAMING" in m for m in messages)
