# python-backend/tests/test_prompt_constant.py
from app.constants.prompt import PromptConstant


def test_get_returns_zh_by_default():
    result = PromptConstant.get("AGENT1_TITLE_PROMPT")
    assert result == PromptConstant.AGENT1_TITLE_PROMPT


def test_get_returns_zh_explicitly():
    result = PromptConstant.get("AGENT1_TITLE_PROMPT", "zh")
    assert result == PromptConstant.AGENT1_TITLE_PROMPT


def test_get_returns_en_when_available():
    result = PromptConstant.get("AGENT1_TITLE_PROMPT", "en")
    assert result == PromptConstant.AGENT1_TITLE_PROMPT_EN
    assert "topic" in result.lower() or "title" in result.lower()


def test_get_falls_back_to_zh_when_en_missing():
    # AGENT5_IMAGE_EXECUTION_PROMPT has no _EN variant, should fall back to Chinese
    result = PromptConstant.get("AGENT5_IMAGE_EXECUTION_PROMPT", "en")
    assert result == PromptConstant.AGENT5_IMAGE_EXECUTION_PROMPT


def test_get_style_instruction_zh():
    result = PromptConstant.get_style_instruction("POPULAR", "zh")
    assert "爆款" in result


def test_get_style_instruction_en():
    result = PromptConstant.get_style_instruction("POPULAR", "en")
    assert result  # Not empty
    assert "爆款" not in result  # Not the Chinese version


def test_get_style_instruction_unknown_style():
    result = PromptConstant.get_style_instruction("UNKNOWN", "en")
    assert result == ""


def test_all_en_variants_differ_from_zh():
    for name in [
        "AGENT1_TITLE_PROMPT",
        "AGENT2_DESCRIPTION_SECTION",
        "AGENT2_OUTLINE_PROMPT",
        "AGENT3_CONTENT_PROMPT",
        "AGENT4_IMAGE_REQUIREMENTS_PROMPT",
        "AI_MODIFY_OUTLINE_PROMPT",
    ]:
        en_val = PromptConstant.get(name, "en")
        zh_val = PromptConstant.get(name, "zh")
        assert en_val != zh_val, f"{name}_EN should differ from {name}"
