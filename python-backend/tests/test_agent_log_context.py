import pytest
from unittest.mock import MagicMock, AsyncMock


@pytest.mark.asyncio
async def test_context_records_success():
    """成功执行时 status=SUCCESS，save_log_async 被调用"""
    from app.services.article.article_agent_service import ArticleAgentService

    svc = ArticleAgentService.__new__(ArticleAgentService)
    mock_log_svc = MagicMock()
    svc.agent_log_service = mock_log_svc

    async with svc._agent_log_context(
        task_id="t1",
        agent_name="agent1_generate_titles",
        input_data={"topic": "AI"},
    ) as log_data:
        log_data["outputData"] = '{"count": 3}'

    assert mock_log_svc.save_log_async.called
    call_args = mock_log_svc.save_log_async.call_args[0][0]
    assert call_args["status"] == "SUCCESS"
    assert call_args["taskId"] == "t1"
    assert call_args["agentName"] == "agent1_generate_titles"
    assert call_args["durationMs"] >= 0
    assert call_args["endTime"] is not None


@pytest.mark.asyncio
async def test_context_records_failure():
    """抛出异常时 status=FAILED，异常被重新抛出"""
    from app.services.article.article_agent_service import ArticleAgentService

    svc = ArticleAgentService.__new__(ArticleAgentService)
    svc.agent_log_service = MagicMock()

    with pytest.raises(ValueError, match="LLM failed"):
        async with svc._agent_log_context(task_id="t2", agent_name="agent2_generate_outline"):
            raise ValueError("LLM failed")

    call_args = svc.agent_log_service.save_log_async.call_args[0][0]
    assert call_args["status"] == "FAILED"
    assert "LLM failed" in call_args["errorMessage"]


def test_context_sync_records_success():
    """同步版上下文管理器成功执行时 status=SUCCESS"""
    from app.services.article.article_agent_service import ArticleAgentService

    svc = ArticleAgentService.__new__(ArticleAgentService)
    svc.agent_log_service = MagicMock()

    with svc._agent_log_context_sync(task_id="t3", agent_name="agent6_merge_content") as log_data:
        log_data["outputData"] = '{"length": 500}'

    call_args = svc.agent_log_service.save_log_async.call_args[0][0]
    assert call_args["status"] == "SUCCESS"
    assert call_args["agentName"] == "agent6_merge_content"
