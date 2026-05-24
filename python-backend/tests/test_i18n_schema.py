# tests/test_i18n_schema.py
from app.schemas.article import ArticleCreateRequest, ArticleState


def test_article_create_request_default_language():
    req = ArticleCreateRequest(topic="测试选题")
    assert req.language == 'zh'


def test_article_create_request_en_language():
    req = ArticleCreateRequest(topic="Test topic", language="en")
    assert req.language == 'en'


def test_article_state_default_language():
    state = ArticleState()
    assert state.language == 'zh'


def test_article_state_set_language():
    state = ArticleState()
    state.language = 'en'
    assert state.language == 'en'
