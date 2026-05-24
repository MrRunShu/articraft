import asyncio
import base64
import logging
import tempfile
from pathlib import Path
from typing import Optional

from openai import AsyncOpenAI

from app.config import settings
from app.models.enums import ImageMethodEnum
from app.services.image.image_search_service import ImageData, ImageRequest, ImageSearchService

logger = logging.getLogger(__name__)

MERMAID_TEMPLATE = """graph TD
    A[开始] --> B{判断}
    B -->|是| C[执行操作]
    B -->|否| D[跳过]
    C --> E[结束]
    D --> E
"""


class MermaidService(ImageSearchService):
    """Mermaid 流程图服务（CLI 渲染）"""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.deepseek_api_key, base_url="https://api.deepseek.com")
        self.model = settings.deepseek_model

    def get_method(self) -> ImageMethodEnum:
        return ImageMethodEnum.MERMAID

    async def search(self, request: ImageRequest) -> Optional[ImageData]:
        try:
            # 先用 AI 生成 Mermaid 代码，再渲染
            mermaid_code = await self._generate_mermaid_code(request.keywords, request.description)
            if not mermaid_code:
                return None
            svg_content = await self._render_mermaid(mermaid_code)
            if not svg_content:
                return None
            b64 = base64.b64encode(svg_content.encode()).decode()
            data_url = f"data:image/svg+xml;base64,{b64}"
            return ImageData(url=data_url, method=ImageMethodEnum.MERMAID)
        except Exception as e:
            logger.error(f"Mermaid 生成异常: {e}")
            return None

    async def _generate_mermaid_code(self, keywords: str, description: str) -> Optional[str]:
        """用 AI 生成适合内容的 Mermaid 代码"""
        try:
            prompt = f"""根据以下关键词，生成一段简洁的 Mermaid 流程图代码（graph TD 格式）：
关键词：{keywords}
说明：{description}

要求：
1. 只返回 Mermaid 代码，不要加 ```mermaid 标记
2. 节点文字用中文
3. 控制在 5-8 个节点以内
4. 使用 graph TD 方向"""
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
            )
            code = response.choices[0].message.content.strip()
            # 去掉可能的代码块标记
            if code.startswith("```"):
                lines = code.split("\n")
                code = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            return code if code.startswith("graph") else None
        except Exception as e:
            logger.error(f"Mermaid 代码生成失败: {e}")
            return None

    async def _render_mermaid(self, mermaid_code: str) -> Optional[str]:
        """通过 mmdc CLI 渲染 Mermaid 为 SVG"""
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                input_file = Path(tmp_dir) / "diagram.mmd"
                output_file = Path(tmp_dir) / "diagram.svg"
                input_file.write_text(mermaid_code, encoding="utf-8")
                proc = await asyncio.create_subprocess_exec(
                    "mmdc", "-i", str(input_file), "-o", str(output_file),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await asyncio.wait_for(proc.communicate(), timeout=30)
                if output_file.exists():
                    return output_file.read_text(encoding="utf-8")
            return None
        except Exception as e:
            logger.error(f"mmdc 渲染失败（未安装或超时）: {e}")
            return None
