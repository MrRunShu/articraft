import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.agent_log_service import AgentLogService
from app.schemas.statistics import AgentLogVO


# ─── _to_vo 纯函数测试 ──────────────────────────────────────────

def make_service():
    """创建带 mock db 的 AgentLogService"""
    mock_db = MagicMock()
    return AgentLogService(mock_db)


def test_to_vo_success_row():
    svc = make_service()
    now = datetime(2026, 5, 22, 10, 0, 0)
    row = {
        "id": 1,
        "taskId": "task-abc",
        "agentName": "agent1_generate_titles",
        "startTime": now,
        "endTime": now,
        "durationMs": 1500,
        "status": "SUCCESS",
        "errorMessage": None,
        "prompt": "test prompt",
        "inputData": '{"topic": "AI"}',
        "outputData": '{"optionsCount": 3}',
        "createTime": now,
        "updateTime": now,
    }
    vo = svc._to_vo(row)
    assert vo.task_id == "task-abc"
    assert vo.agent_name == "agent1_generate_titles"
    assert vo.duration_ms == 1500
    assert vo.status == "SUCCESS"
    assert vo.error_message is None
    assert "2026-05-22" in vo.start_time


def test_to_vo_failed_row():
    svc = make_service()
    now = datetime(2026, 5, 22, 10, 0, 0)
    row = {
        "id": 2,
        "taskId": "task-xyz",
        "agentName": "agent2_generate_outline",
        "startTime": now,
        "endTime": now,
        "durationMs": 200,
        "status": "FAILED",
        "errorMessage": "LLM timeout",
        "prompt": None,
        "inputData": None,
        "outputData": None,
        "createTime": now,
        "updateTime": now,
    }
    vo = svc._to_vo(row)
    assert vo.status == "FAILED"
    assert vo.error_message == "LLM timeout"


def test_to_iso_none():
    svc = make_service()
    assert AgentLogService._to_iso(None) is None


def test_to_iso_datetime():
    dt = datetime(2026, 5, 22, 10, 30, 0)
    result = AgentLogService._to_iso(dt)
    assert result == "2026-05-22T10:30:00"


# ─── get_execution_stats 逻辑测试（mock get_logs_by_task_id）──────

@pytest.mark.asyncio
async def test_get_execution_stats_no_logs():
    svc = make_service()
    svc.get_logs_by_task_id = AsyncMock(return_value=[])

    result = await svc.get_execution_stats("task-empty")
    assert result.task_id == "task-empty"
    assert result.total_duration_ms == 0
    assert result.overall_status == "NOT_FOUND"
    assert result.logs == []


@pytest.mark.asyncio
async def test_get_execution_stats_all_success():
    svc = make_service()
    now = datetime(2026, 5, 22, 10, 0, 0)

    logs = [
        AgentLogVO(
            id=1, taskId="t1", agentName="agent1_generate_titles",
            startTime=now.isoformat(), durationMs=1000, status="SUCCESS",
            createTime=now.isoformat(), updateTime=now.isoformat(),
        ),
        AgentLogVO(
            id=2, taskId="t1", agentName="agent2_generate_outline",
            startTime=now.isoformat(), durationMs=2000, status="SUCCESS",
            createTime=now.isoformat(), updateTime=now.isoformat(),
        ),
    ]
    svc.get_logs_by_task_id = AsyncMock(return_value=logs)

    result = await svc.get_execution_stats("t1")
    assert result.total_duration_ms == 3000
    assert result.agent_count == 2
    assert result.overall_status == "SUCCESS"
    assert result.agent_durations["agent1_generate_titles"] == 1000


@pytest.mark.asyncio
async def test_get_execution_stats_has_failed():
    svc = make_service()
    now = datetime(2026, 5, 22, 10, 0, 0)

    logs = [
        AgentLogVO(
            id=1, taskId="t2", agentName="agent1_generate_titles",
            startTime=now.isoformat(), durationMs=500, status="SUCCESS",
            createTime=now.isoformat(), updateTime=now.isoformat(),
        ),
        AgentLogVO(
            id=2, taskId="t2", agentName="agent2_generate_outline",
            startTime=now.isoformat(), durationMs=100, status="FAILED",
            errorMessage="timeout",
            createTime=now.isoformat(), updateTime=now.isoformat(),
        ),
    ]
    svc.get_logs_by_task_id = AsyncMock(return_value=logs)

    result = await svc.get_execution_stats("t2")
    assert result.overall_status == "FAILED"
    assert result.total_duration_ms == 600
