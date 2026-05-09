import json
import pytest


def make_agent_service():
    """创建 ArticleAgentService 实例但跳过 __init__（避免读取 config）"""
    from app.services.article_agent_service import ArticleAgentService
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
