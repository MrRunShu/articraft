from typing import Callable


class StreamHandlerContext:
    """统一封装流式消息输出，提供语义化的 emit 方法"""

    def __init__(self, stream_handler: Callable[[str], None]):
        self._stream_handler = stream_handler

    def emit(self, message: str) -> None:
        """透传 SSE 消息"""
        self._stream_handler(message)
