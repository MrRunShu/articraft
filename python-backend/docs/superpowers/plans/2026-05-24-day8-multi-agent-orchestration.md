# Day 8 多智能体编排 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 5 个智能体的调用逻辑从 `ArticleAgentService` 中拆分到独立 Agent 类，通过编排器统一协调，并用 `asyncio.Semaphore` 实现并行配图生成。

**Architecture:** 新建 `app/agent/` 包，包含 agents（5个适配器）、context（流式上下文）、parallel（并行图片生成器）、orchestrator（编排器）四个子模块。`ArticleAgentService` 的三个 `execute_phase*` 方法改为委托给编排器，`agent5_generate_images` 改为使用并行生成器。前端无需修改。

**Tech Stack:** Python asyncio, asyncio.Semaphore, asyncio.gather, FastAPI/uvicorn (already in place)

---

## 文件结构

**新建文件：**
- `python-backend/app/agent/__init__.py`
- `python-backend/app/agent/agents/__init__.py`
- `python-backend/app/agent/agents/title_generator.py` — `TitleGeneratorAgent`
- `python-backend/app/agent/agents/outline_generator.py` — `OutlineGeneratorAgent`
- `python-backend/app/agent/agents/content_generator.py` — `ContentGeneratorAgent`
- `python-backend/app/agent/agents/image_analyzer.py` — `ImageAnalyzerAgent`
- `python-backend/app/agent/agents/content_merger.py` — `ContentMergerAgent`
- `python-backend/app/agent/context/__init__.py`
- `python-backend/app/agent/context/stream_handler.py` — `StreamHandlerContext`
- `python-backend/app/agent/parallel/__init__.py`
- `python-backend/app/agent/parallel/image_generator.py` — `ParallelImageGenerator`
- `python-backend/app/agent/orchestrator.py` — `ArticleAgentOrchestrator`

**修改文件：**
- `python-backend/.env` — 新增 2 个配置项
- `python-backend/app/config.py` — 新增 2 个 Settings 字段
- `python-backend/app/constants/article.py` — 新增 2 个常量
- `python-backend/app/constants/prompt.py` — 新增 `AGENT5_IMAGE_EXECUTION_PROMPT`
- `python-backend/app/services/article_agent_service.py` — 初始化编排器+并行生成器，委托三个阶段，重写 agent5

---

### Task 1: 配置与常量

**Files:**
- Modify: `python-backend/.env`
- Modify: `python-backend/app/config.py`
- Modify: `python-backend/app/constants/article.py`
- Modify: `python-backend/app/constants/prompt.py`

- [ ] **Step 1: 在 `.env` 末尾追加两个新配置项**

在 `python-backend/.env` 文件末尾添加：
```
# Day 8：多智能体并行编排
AGENT_IMAGE_MAX_CONCURRENCY=3
AGENT_IMAGE_FAIL_FAST=true
```

- [ ] **Step 2: 在 `config.py` 的 Settings 类中添加两个字段**

在 `python-backend/app/config.py` 的 `Settings` 类中，在 `stripe_cancel_url` 字段之后、`model_config` 之前添加：
```python
    # Day 8：多智能体并行编排配置
    agent_image_max_concurrency: int = 3
    agent_image_fail_fast: bool = True
```

- [ ] **Step 3: 在 `article.py` 常量中添加两个默认值常量**

将 `python-backend/app/constants/article.py` 改为：
```python
class ArticleConstant:
    SSE_TIMEOUT_MS = 30 * 60 * 1000
    SSE_RECONNECT_TIME_MS = 3000

    PEXELS_API_URL = "https://api.pexels.com/v1/search"
    PEXELS_PER_PAGE = 1
    PEXELS_ORIENTATION_LANDSCAPE = "landscape"

    PICSUM_URL_TEMPLATE = "https://picsum.photos/800/600?random={}"

    # Day 8：并行配图默认配置
    AGENT_IMAGE_MAX_CONCURRENCY = 3
    AGENT_IMAGE_FAIL_FAST = True
```

- [ ] **Step 4: 在 `prompt.py` 中追加 AGENT5_IMAGE_EXECUTION_PROMPT 常量**

在 `python-backend/app/constants/prompt.py` 的 `PromptConstant` 类中，在 `AI_MODIFY_OUTLINE_PROMPT` 之后、`STYLE_INSTRUCTIONS` 之前添加：
```python
    # Day 8：并行配图执行说明（用于日志与编排标识）
    AGENT5_IMAGE_EXECUTION_PROMPT = "并行执行配图生成，确保结果按 position 顺序回填。"
```

- [ ] **Step 5: 验证配置加载**

```bash
cd python-backend
uv run python -c "from app.config import settings; print(settings.agent_image_max_concurrency, settings.agent_image_fail_fast)"
```
预期输出：`3 True`

- [ ] **Step 6: 提交**

```bash
git add python-backend/.env python-backend/app/config.py python-backend/app/constants/article.py python-backend/app/constants/prompt.py
git commit -m "feat(day8): add parallel image config and constants"
```

---

### Task 2: StreamHandlerContext + 5 个 Agent 适配器

**Files:**
- Create: `python-backend/app/agent/__init__.py`
- Create: `python-backend/app/agent/context/__init__.py`
- Create: `python-backend/app/agent/context/stream_handler.py`
- Create: `python-backend/app/agent/agents/__init__.py`
- Create: `python-backend/app/agent/agents/title_generator.py`
- Create: `python-backend/app/agent/agents/outline_generator.py`
- Create: `python-backend/app/agent/agents/content_generator.py`
- Create: `python-backend/app/agent/agents/image_analyzer.py`
- Create: `python-backend/app/agent/agents/content_merger.py`

- [ ] **Step 1: 创建包初始化文件**

创建以下三个空文件（内容均为空）：
- `python-backend/app/agent/__init__.py`
- `python-backend/app/agent/context/__init__.py`
- `python-backend/app/agent/agents/__init__.py`

- [ ] **Step 2: 创建 StreamHandlerContext**

创建 `python-backend/app/agent/context/stream_handler.py`：
```python
from typing import Callable


class StreamHandlerContext:
    """统一封装流式消息输出，提供语义化的 emit 方法"""

    def __init__(self, stream_handler: Callable[[str], None]):
        self._stream_handler = stream_handler

    def emit(self, message: str) -> None:
        """透传 SSE 消息"""
        self._stream_handler(message)
```

- [ ] **Step 3: 创建 TitleGeneratorAgent**

创建 `python-backend/app/agent/agents/title_generator.py`：
```python
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.schemas.article import ArticleState
    from app.services.article_agent_service import ArticleAgentService


class TitleGeneratorAgent:
    """标题生成智能体适配器：委托给 service.agent1_generate_title_options"""

    async def run(self, service: "ArticleAgentService", state: "ArticleState") -> None:
        await service.agent1_generate_title_options(state)
```

- [ ] **Step 4: 创建 OutlineGeneratorAgent**

创建 `python-backend/app/agent/agents/outline_generator.py`：
```python
from __future__ import annotations
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from app.schemas.article import ArticleState
    from app.services.article_agent_service import ArticleAgentService


class OutlineGeneratorAgent:
    """大纲生成智能体适配器：委托给 service.agent2_generate_outline（需流式输出）"""

    async def run(
        self,
        service: "ArticleAgentService",
        state: "ArticleState",
        stream_handler: Callable[[str], None],
    ) -> None:
        await service.agent2_generate_outline(state, stream_handler)
```

- [ ] **Step 5: 创建 ContentGeneratorAgent**

创建 `python-backend/app/agent/agents/content_generator.py`：
```python
from __future__ import annotations
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from app.schemas.article import ArticleState
    from app.services.article_agent_service import ArticleAgentService


class ContentGeneratorAgent:
    """正文生成智能体适配器：委托给 service.agent3_generate_content（需流式输出）"""

    async def run(
        self,
        service: "ArticleAgentService",
        state: "ArticleState",
        stream_handler: Callable[[str], None],
    ) -> None:
        await service.agent3_generate_content(state, stream_handler)
```

- [ ] **Step 6: 创建 ImageAnalyzerAgent**

创建 `python-backend/app/agent/agents/image_analyzer.py`：
```python
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.schemas.article import ArticleState
    from app.services.article_agent_service import ArticleAgentService


class ImageAnalyzerAgent:
    """配图需求分析智能体适配器：委托给 service.agent4_analyze_image_requirements"""

    async def run(self, service: "ArticleAgentService", state: "ArticleState") -> None:
        await service.agent4_analyze_image_requirements(state)
```

- [ ] **Step 7: 创建 ContentMergerAgent**

创建 `python-backend/app/agent/agents/content_merger.py`：
```python
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.schemas.article import ArticleState
    from app.services.article_agent_service import ArticleAgentService


class ContentMergerAgent:
    """图文合并智能体适配器：委托给 service.merge_images_into_content（同步）"""

    def run(self, service: "ArticleAgentService", state: "ArticleState") -> None:
        service.merge_images_into_content(state)
```

- [ ] **Step 8: 验证模块可正常导入**

```bash
cd python-backend
uv run python -c "
from app.agent.context.stream_handler import StreamHandlerContext
from app.agent.agents.title_generator import TitleGeneratorAgent
from app.agent.agents.outline_generator import OutlineGeneratorAgent
from app.agent.agents.content_generator import ContentGeneratorAgent
from app.agent.agents.image_analyzer import ImageAnalyzerAgent
from app.agent.agents.content_merger import ContentMergerAgent
print('all imports OK')
"
```
预期输出：`all imports OK`

- [ ] **Step 9: 提交**

```bash
git add python-backend/app/agent/
git commit -m "feat(day8): add StreamHandlerContext and 5 agent adapter classes"
```

---

### Task 3: ParallelImageGenerator

**Files:**
- Create: `python-backend/app/agent/parallel/__init__.py`
- Create: `python-backend/app/agent/parallel/image_generator.py`

- [ ] **Step 1: 创建包初始化文件**

创建空文件 `python-backend/app/agent/parallel/__init__.py`

- [ ] **Step 2: 创建 ParallelImageGenerator**

创建 `python-backend/app/agent/parallel/image_generator.py`：
```python
import asyncio
import logging
from typing import List, Tuple

from app.models.enums import ImageMethodEnum
from app.schemas.article import ImageRequirement
from app.services.cos_service import CosService
from app.services.image_search_service import ImageData, ImageRequest
from app.services.image_strategy_service import ImageServiceStrategy

logger = logging.getLogger(__name__)


class ParallelImageGenerator:
    """
    并行配图生成器。
    用 asyncio.Semaphore 控制最大并发数，asyncio.gather 同时提交所有任务。
    返回 (ImageRequirement, ImageData, cos_url) 三元组列表，顺序与输入一致（调用方负责排序）。
    """

    def __init__(
        self,
        image_strategy: ImageServiceStrategy,
        cos_service: CosService,
        max_concurrency: int,
        fail_fast: bool,
    ):
        self.image_strategy = image_strategy
        self.cos_service = cos_service
        self.max_concurrency = max(1, max_concurrency)
        self.fail_fast = fail_fast

    async def generate(
        self,
        requirements: List[ImageRequirement],
    ) -> List[Tuple[ImageRequirement, ImageData, str]]:
        """
        并行生成配图并上传至 COS。
        返回成功完成的 (requirement, image_data, cos_url) 列表。
        如果 fail_fast=True 且存在失败，抛出第一个异常；否则返回所有成功结果。
        """
        if not requirements:
            return []

        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def _generate_single(
            requirement: ImageRequirement,
        ) -> Tuple[ImageRequirement, ImageData, str]:
            async with semaphore:
                try:
                    method_enum = ImageMethodEnum(requirement.image_method)
                except ValueError:
                    method_enum = ImageMethodEnum.PEXELS

                image_request = ImageRequest(
                    keywords=requirement.keywords,
                    position=requirement.position,
                    image_method=method_enum,
                    section_title=requirement.section_title,
                    description=f"{requirement.type} image for {requirement.section_title or 'cover'}",
                )
                image_data = await self.image_strategy.get_image(image_request)
                cos_url = await self.cos_service.upload_async(image_data.url)
                logger.info(
                    "ParallelImageGenerator: 配图生成成功, position=%s, method=%s",
                    requirement.position,
                    image_data.method.value,
                )
                return requirement, image_data, cos_url

        raw_results = await asyncio.gather(
            *[_generate_single(req) for req in requirements],
            return_exceptions=True,
        )

        generated: List[Tuple[ImageRequirement, ImageData, str]] = []
        first_error: Exception | None = None
        for item in raw_results:
            if isinstance(item, Exception):
                logger.error("ParallelImageGenerator: 单张配图生成失败, error=%s", item)
                if first_error is None:
                    first_error = item
                continue
            generated.append(item)

        if first_error and (self.fail_fast or not generated):
            raise first_error

        return generated
```

- [ ] **Step 3: 验证模块可导入**

```bash
cd python-backend
uv run python -c "
from app.agent.parallel.image_generator import ParallelImageGenerator
print('ParallelImageGenerator import OK')
"
```
预期输出：`ParallelImageGenerator import OK`

- [ ] **Step 4: 提交**

```bash
git add python-backend/app/agent/parallel/
git commit -m "feat(day8): add ParallelImageGenerator with asyncio.Semaphore concurrency control"
```

---

### Task 4: ArticleAgentOrchestrator

**Files:**
- Create: `python-backend/app/agent/orchestrator.py`

- [ ] **Step 1: 创建编排器**

创建 `python-backend/app/agent/orchestrator.py`：
```python
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable

from app.agent.agents.content_generator import ContentGeneratorAgent
from app.agent.agents.content_merger import ContentMergerAgent
from app.agent.agents.image_analyzer import ImageAnalyzerAgent
from app.agent.agents.outline_generator import OutlineGeneratorAgent
from app.agent.agents.title_generator import TitleGeneratorAgent
from app.agent.context.stream_handler import StreamHandlerContext
from app.models.enums import SseMessageTypeEnum

if TYPE_CHECKING:
    from app.schemas.article import ArticleState
    from app.services.article_agent_service import ArticleAgentService

logger = logging.getLogger(__name__)


class ArticleAgentOrchestrator:
    """
    多智能体编排器。
    持有所有 Agent 实例，按阶段驱动执行，负责推送阶段完成的 SSE 消息。
    不直接包含业务逻辑，全部委托给 ArticleAgentService 的对应方法。
    """

    def __init__(self):
        self.title_agent = TitleGeneratorAgent()
        self.outline_agent = OutlineGeneratorAgent()
        self.content_agent = ContentGeneratorAgent()
        self.image_analyzer_agent = ImageAnalyzerAgent()
        self.content_merger_agent = ContentMergerAgent()

    async def execute_phase1(
        self,
        service: "ArticleAgentService",
        state: "ArticleState",
        stream_handler: Callable[[str], None],
    ) -> None:
        """阶段1：生成标题方案"""
        stream_context = StreamHandlerContext(stream_handler)
        logger.info("阶段1：开始生成标题方案, taskId=%s", state.task_id)
        await self.title_agent.run(service, state)
        stream_context.emit(SseMessageTypeEnum.AGENT1_COMPLETE.value)
        logger.info(
            "阶段1：标题方案生成成功, taskId=%s, optionsCount=%s",
            state.task_id,
            len(state.title_options or []),
        )

    async def execute_phase2(
        self,
        service: "ArticleAgentService",
        state: "ArticleState",
        stream_handler: Callable[[str], None],
    ) -> None:
        """阶段2：生成大纲（流式输出）"""
        stream_context = StreamHandlerContext(stream_handler)
        logger.info("阶段2：开始生成大纲, taskId=%s", state.task_id)
        await self.outline_agent.run(service, state, stream_context.emit)
        stream_context.emit(SseMessageTypeEnum.AGENT2_COMPLETE.value)
        logger.info("阶段2：大纲生成成功, taskId=%s", state.task_id)

    async def execute_phase3(
        self,
        service: "ArticleAgentService",
        state: "ArticleState",
        stream_handler: Callable[[str], None],
    ) -> None:
        """阶段3：正文生成 → 配图分析 → 配图生成 → 图文合并"""
        stream_context = StreamHandlerContext(stream_handler)

        logger.info("阶段3：开始生成正文, taskId=%s", state.task_id)
        await self.content_agent.run(service, state, stream_context.emit)
        stream_context.emit(SseMessageTypeEnum.AGENT3_COMPLETE.value)

        logger.info("阶段3：开始分析配图需求, taskId=%s", state.task_id)
        await self.image_analyzer_agent.run(service, state)
        stream_context.emit(SseMessageTypeEnum.AGENT4_COMPLETE.value)

        # agent5 保留在 service 中（与 SSE 推送深度交互）
        logger.info("阶段3：开始生成配图, taskId=%s", state.task_id)
        await service.agent5_generate_images(state, stream_context.emit)
        stream_context.emit(SseMessageTypeEnum.AGENT5_COMPLETE.value)

        logger.info("阶段3：开始图文合成, taskId=%s", state.task_id)
        self.content_merger_agent.run(service, state)
        stream_context.emit(SseMessageTypeEnum.MERGE_COMPLETE.value)
```

- [ ] **Step 2: 验证编排器可导入**

```bash
cd python-backend
uv run python -c "
from app.agent.orchestrator import ArticleAgentOrchestrator
o = ArticleAgentOrchestrator()
print('orchestrator OK, agents:', o.title_agent, o.outline_agent, o.content_agent)
"
```
预期：打印出各 agent 对象而不报错。

- [ ] **Step 3: 提交**

```bash
git add python-backend/app/agent/orchestrator.py
git commit -m "feat(day8): add ArticleAgentOrchestrator with three-phase execution"
```

---

### Task 5: 集成到 ArticleAgentService

**Files:**
- Modify: `python-backend/app/services/article_agent_service.py`

这是本次重构的最后一步，也是改动最集中的地方。我们要做三件事：
1. `__init__` 中初始化 `ParallelImageGenerator` 和 `ArticleAgentOrchestrator`
2. 三个 `execute_phase*` 方法改为委托给编排器
3. `agent5_generate_images` 改为使用并行生成器

- [ ] **Step 1: 修改 `__init__` — 新增导入和初始化**

在 `article_agent_service.py` 顶部的 import 区域，在现有 import 之后添加：
```python
from app.agent.orchestrator import ArticleAgentOrchestrator
from app.agent.parallel.image_generator import ParallelImageGenerator
```

在 `ArticleAgentService.__init__` 方法中，在 `self.agent_log_service = AgentLogService(database)` 之后添加：
```python
        self.image_service_strategy = ImageServiceStrategy()
        self.parallel_image_generator = ParallelImageGenerator(
            image_strategy=self.image_service_strategy,
            cos_service=self.cos_service,
            max_concurrency=settings.agent_image_max_concurrency,
            fail_fast=settings.agent_image_fail_fast,
        )
        self.orchestrator = ArticleAgentOrchestrator()
```

注意：原来的 `self.image_strategy = ImageServiceStrategy()` 要**改名**为 `self.image_service_strategy`，同时删除原 `self.image_strategy` 那行，保持只有一个实例。

- [ ] **Step 2: 修改三个 execute_phase 方法委托给编排器**

将三个阶段方法替换为：
```python
    async def execute_phase1_generate_titles(
        self,
        state: ArticleState,
        stream_handler: Callable[[str], None],
    ):
        """阶段1：生成标题方案（委托给编排器）"""
        try:
            await self.orchestrator.execute_phase1(self, state, stream_handler)
        except Exception as e:
            logger.error("阶段1失败, taskId=%s, error=%s", state.task_id, e)
            raise RuntimeError(f"标题方案生成失败: {e}")

    async def execute_phase2_generate_outline(
        self,
        state: ArticleState,
        stream_handler: Callable[[str], None],
    ):
        """阶段2：生成大纲（委托给编排器）"""
        try:
            await self.orchestrator.execute_phase2(self, state, stream_handler)
        except Exception as e:
            logger.error("阶段2失败, taskId=%s, error=%s", state.task_id, e)
            raise RuntimeError(f"大纲生成失败: {e}")

    async def execute_phase3_generate_content(
        self,
        state: ArticleState,
        stream_handler: Callable[[str], None],
    ):
        """阶段3：正文、配图、合并（委托给编排器）"""
        try:
            await self.orchestrator.execute_phase3(self, state, stream_handler)
        except Exception as e:
            logger.error("阶段3失败, taskId=%s, error=%s", state.task_id, e)
            raise RuntimeError(f"正文生成失败: {e}")
```

- [ ] **Step 3: 重写 agent5_generate_images 使用并行生成器**

将原来的 `agent5_generate_images` 方法完整替换为：
```python
    async def agent5_generate_images(
        self, state: ArticleState, stream_handler: Callable[[str], None]
    ):
        """智能体5：并行生成配图（Day 8：使用 ParallelImageGenerator）"""
        async with self._agent_log_context(
            task_id=state.task_id,
            agent_name="agent5_generate_images",
            prompt=PromptConstant.AGENT5_IMAGE_EXECUTION_PROMPT,
            input_data={"requirementsCount": len(state.image_requirements or [])},
        ) as log_data:
            generated_triples = await self.parallel_image_generator.generate(
                state.image_requirements or []
            )
            image_results: List[ImageResult] = []

            for requirement, image_data, cos_url in generated_triples:
                result = ImageResult(
                    position=requirement.position,
                    url=cos_url,
                    method=image_data.method.value,
                    keywords=requirement.keywords,
                    sectionTitle=requirement.section_title,
                    description=f"{requirement.type} image for {requirement.section_title or 'cover'}",
                )
                image_results.append(result)

                msg = (
                    SseMessageTypeEnum.IMAGE_COMPLETE.get_streaming_prefix()
                    + result.model_dump_json(by_alias=True)
                )
                stream_handler(msg)
                logger.info(
                    "智能体5：配图生成并上传成功, position=%s, method=%s, cosUrl=%s",
                    requirement.position,
                    image_data.method.value,
                    cos_url,
                )

            # 并行执行后按位置排序，确保顺序稳定
            state.images = sorted(image_results, key=lambda r: r.position)
            log_data["outputData"] = self._safe_json_dumps(
                {"imagesCount": len(state.images)}
            )
            logger.info("智能体5：所有配图生成完成, count=%s", len(state.images))
```

- [ ] **Step 4: 验证后端能正常启动**

```bash
cd python-backend
uv run uvicorn app.main:app --reload --port 8567
```
预期：看到 `Application startup complete.` 无报错。

- [ ] **Step 5: 验证健康检查**

```bash
curl http://localhost:8567/api/health
```
预期：`{"code":0,"data":"ok","message":"服务正常"}`

- [ ] **Step 6: 提交**

```bash
git add python-backend/app/services/article_agent_service.py
git commit -m "feat(day8): integrate orchestrator and parallel image generator into ArticleAgentService"
```

---

## Self-Review Checklist

**Spec Coverage:**
- [x] 多智能体编排重构（5个 Agent 适配器 + Orchestrator）→ Task 2, 4
- [x] 流处理上下文封装（StreamHandlerContext）→ Task 2
- [x] 并行配图生成（ParallelImageGenerator + asyncio.Semaphore）→ Task 3, 5
- [x] 配置项新增（max_concurrency, fail_fast）→ Task 1
- [x] 集成到 ArticleAgentService → Task 5
- [x] 占位符格式（我们的 prompt 不使用 placeholder，跳过；AGENT5_IMAGE_EXECUTION_PROMPT 已在 Task 1 添加）

**注：** 课程 3.7 节的占位符修复（`{{{{IMAGE_PLACEHOLDER_N}}}}` → `{{IMAGE_PLACEHOLDER_N}}`）不适用于我们的代码库——我们的配图方式是通过 `sectionTitle` 匹配定位插入位置，而非占位符替换。
