import asyncio
import logging
from typing import Dict

from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)


class SseEmitterManager:
    """SSE 管理器：asyncio.Queue + StreamingResponse 实现实时推送"""

    def __init__(self):
        self._queues: Dict[str, asyncio.Queue] = {}

    def create_emitter(self, task_id: str) -> StreamingResponse:
        """为 task_id 创建 SSE 连接，返回 StreamingResponse"""
        queue: asyncio.Queue = asyncio.Queue()
        self._queues[task_id] = queue

        async def event_generator():
            try:
                while True:
                    message = await queue.get()
                    if message == "__COMPLETE__":
                        break
                    yield f"data: {message}\n\n"
            except asyncio.CancelledError:
                pass
            finally:
                self._queues.pop(task_id, None)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    def send(self, task_id: str, message: str):
        """推送一条消息到队列"""
        queue = self._queues.get(task_id)
        if queue is None:
            return
        try:
            queue.put_nowait(message)
        except Exception as e:
            logger.error(f"SSE 消息发送失败, taskId={task_id}, error={e}")

    def complete(self, task_id: str):
        """发送完成信号，关闭 SSE 连接"""
        queue = self._queues.get(task_id)
        if queue is None:
            return
        queue.put_nowait("__COMPLETE__")

    def exists(self, task_id: str) -> bool:
        return task_id in self._queues


sse_emitter_manager = SseEmitterManager()
