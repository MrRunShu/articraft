# i18n 国际化（中英双语）实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 AI 爆款文章创作器添加中英文切换：AppHeader [ZH|EN] 开关，前端 UI 全面 i18n，后端 AI Prompt 随语言切换自动使用对应版本。

**Architecture:** vue-i18n v9 管理前端 UI 语言（localStorage 持久化）；`createArticle` 请求体自动附带 `language` 字段；后端将 `language` 存入 Article DB 列（新增 `language VARCHAR(5) DEFAULT 'zh'`），三个异步阶段均从 DB 读取并注入 `ArticleState.language`；`PromptConstant.get(name, language)` 做双语分发，英文版常量以 `_EN` 后缀命名，缺失时回退中文。

**Tech Stack:** Python/FastAPI + SQLAlchemy（后端），Vue 3 + vue-i18n@9 + TypeScript（前端），MySQL（ALTER TABLE 添加 language 列）

---

## 文件变更总览

**后端新增/修改：**
- Modify: `app/models/article.py` — 添加 `language` 列
- Modify: `app/schemas/article.py` — `ArticleCreateRequest` + `ArticleState` 添加 `language`
- Modify: `app/services/article/article_service.py` — 存储 language、`ai_modify_outline` 传 language
- Modify: `app/services/article/article_async_service.py` — 三个阶段读取并注入 `state.language`
- Modify: `app/routers/article.py` — 创建时传 `request.language`
- Modify: `app/constants/prompt.py` — `get()` 静态方法 + 6 个 `_EN` 常量 + `STYLE_INSTRUCTIONS_EN` + 更新 `get_style_instruction`
- Modify: `app/services/article/article_agent_service.py` — 所有 agent 方法改用 `PromptConstant.get()`
- Create: `tests/test_i18n_schema.py`
- Create: `tests/test_prompt_constant.py`

**前端新增/修改：**
- Install: `vue-i18n@9`
- Create: `src/locales/zh.ts`
- Create: `src/locales/en.ts`
- Create: `src/plugins/i18n.ts`
- Modify: `src/main.ts` — 注册 i18n
- Modify: `src/components/AppHeader.vue` — 语言切换按钮 + 所有文本国际化
- Modify: `src/api/article.ts` — `createArticle` 自动附带 `language`
- Modify: `src/views/article/ArticleCreatePage.vue`
- Modify: `src/views/article/components/TitleSelectingStage.vue`
- Modify: `src/views/article/components/OutlineEditingStage.vue`
- Modify: `src/views/LoginView.vue`
- Modify: `src/views/RegisterView.vue`
- Modify: `src/views/VipPage.vue`
- Modify: `src/views/article/ArticleListPage.vue`
- Modify: `src/views/article/ArticleDetailPage.vue`
- Modify: `src/views/admin/StatisticsPage.vue`

---

## Task 1: 后端 Schema + Article 模型 — 添加 language 字段

**Files:**
- Modify: `python-backend/app/schemas/article.py`
- Modify: `python-backend/app/models/article.py`
- Create: `python-backend/tests/test_i18n_schema.py`

- [ ] **Step 1: 写失败测试**

```python
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
```

- [ ] **Step 2: 运行测试确认失败**

```
cd python-backend
pytest tests/test_i18n_schema.py -v
```
期望：FAIL — `ArticleCreateRequest` 没有 `language` 字段

- [ ] **Step 3: 修改 `app/schemas/article.py`**

在 `ArticleCreateRequest` 中添加 `language` 字段（第 81 行 `style` 字段之后）：

```python
class ArticleCreateRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=500)
    style: Optional[str] = Field(default="POPULAR")
    enabled_image_methods: Optional[List[str]] = Field(None, alias="enabledImageMethods")
    language: str = Field(default='zh')   # 新增：'zh' | 'en'

    class Config:
        populate_by_name = True
```

在 `ArticleState.__init__` 末尾添加 `language` 属性（第 75 行 `full_content` 之后）：

```python
class ArticleState:
    """智能体之间共享的状态容器（非Pydantic，仅内存传递）"""

    def __init__(self):
        self.task_id: Optional[str] = None
        self.topic: Optional[str] = None
        self.user_description: Optional[str] = None
        self.style: str = "POPULAR"
        self.phase: Optional[str] = None
        self.title_options: Optional[List[TitleOption]] = None
        self.enabled_image_methods: Optional[List[str]] = None
        self.title: Optional[TitleResult] = None
        self.outline: Optional[OutlineResult] = None
        self.content: Optional[str] = None
        self.image_requirements: Optional[List[ImageRequirement]] = None
        self.images: Optional[List[ImageResult]] = None
        self.cover_image: Optional[str] = None
        self.full_content: Optional[str] = None
        self.language: str = 'zh'   # 新增：'zh' | 'en'
```

- [ ] **Step 4: 修改 `app/models/article.py` — 添加 language 列**

在 `style` 列之后（第 14 行之后）添加：

```python
    style = Column(String(20), nullable=True, default="POPULAR")
    language = Column(String(5), nullable=False, default='zh', comment="文章语言：zh | en")  # 新增
```

- [ ] **Step 5: 执行 DB 迁移**

```sql
-- 在 MySQL 中执行
ALTER TABLE article ADD COLUMN language VARCHAR(5) NOT NULL DEFAULT 'zh' COMMENT '文章语言：zh | en';
```

通过 MySQL Workbench 或命令行执行。验证：

```sql
DESCRIBE article;
-- 确认出现 language 列
```

- [ ] **Step 6: 运行测试确认通过**

```
cd python-backend
pytest tests/test_i18n_schema.py -v
```
期望：4 tests PASS

- [ ] **Step 7: Commit**

```
git add app/schemas/article.py app/models/article.py tests/test_i18n_schema.py
git commit -m "feat(i18n): add language field to ArticleCreateRequest, ArticleState, Article model"
```

---

## Task 2: 后端 — Service 层贯穿 language 字段

**Files:**
- Modify: `python-backend/app/services/article/article_service.py`
- Modify: `python-backend/app/services/article/article_async_service.py`
- Modify: `python-backend/app/routers/article.py`

- [ ] **Step 1: 修改 `article_service.py` — `create_article_task_with_quota_check` 存入 language**

找到 `create_article_task_with_quota_check` 方法签名（约第 30 行），添加 `language` 参数：

```python
async def create_article_task_with_quota_check(
    self,
    topic: str,
    login_user: LoginUserVO,
    style: str = "POPULAR",
    enabled_image_methods: Optional[List[str]] = None,
    language: str = 'zh',   # 新增
) -> str:
```

在 `insert(Article).values(...)` 中添加 `language=language`（在 `is_delete=0` 之前）：

```python
        await self.db.execute(
            insert(Article).values(
                task_id=task_id,
                user_id=login_user.id,
                topic=topic,
                style=style,
                language=language,   # 新增
                status=ArticleStatusEnum.PENDING.value,
                phase=ArticlePhaseEnum.PENDING.value,
                enabled_image_methods=(
                    json.dumps(enabled_image_methods, ensure_ascii=False)
                    if enabled_image_methods
                    else None
                ),
                create_time=now,
                update_time=now,
                is_delete=0,
            )
        )
```

- [ ] **Step 2: 修改 `article_service.py` — `ai_modify_outline` 传 language**

在 `ai_modify_outline` 方法中，读取 `language` 并传给 agent_service（约第 196 行）：

```python
        modified_outline = await agent_service.ai_modify_outline(
            main_title=article["mainTitle"],
            sub_title=article["subTitle"],
            current_outline=current_outline,
            modify_suggestion=modify_suggestion,
            task_id=task_id,
            language=article.get("language", "zh"),   # 新增
        )
```

- [ ] **Step 3: 修改 `article_async_service.py` — `execute_phase1` 接收并注入 language**

更新方法签名（约第 25 行）：

```python
    async def execute_phase1(
        self,
        task_id: str,
        topic: str,
        style: Optional[str] = None,
        language: str = 'zh',   # 新增
    ):
```

在 `state = ArticleState()` 构建块中（约第 40 行）添加：

```python
            state = ArticleState()
            state.task_id = task_id
            state.topic = topic
            state.style = style or "POPULAR"
            state.language = language   # 新增
```

- [ ] **Step 4: 修改 `article_async_service.py` — `execute_phase2` 从 DB 读取 language**

在 `state = ArticleState()` 构建块中（约第 80 行）添加：

```python
            state = ArticleState()
            state.task_id = task_id
            state.style = article["style"] or "POPULAR"
            state.language = article.get("language", "zh")   # 新增
            state.user_description = article["userDescription"]
            state.title = TitleResult(
                mainTitle=article["mainTitle"],
                subTitle=article["subTitle"],
            )
```

- [ ] **Step 5: 修改 `article_async_service.py` — `execute_phase3` 从 DB 读取 language**

在 `state = ArticleState()` 构建块中（约第 133 行）添加：

```python
            state = ArticleState()
            state.task_id = task_id
            state.style = article["style"] or "POPULAR"
            state.language = article.get("language", "zh")   # 新增
            state.enabled_image_methods = enabled_methods
            state.title = TitleResult(
                mainTitle=article["mainTitle"],
                subTitle=article["subTitle"],
            )
```

- [ ] **Step 6: 修改 `app/routers/article.py` — 传 language 给 execute_phase1**

找到 `create_article` 路由（约第 43 行），更新 `execute_phase1` 调用：

```python
    asyncio.create_task(
        article_async_service.execute_phase1(task_id, request.topic, style, request.language)
    )
```

同时更新 `create_article_task_with_quota_check` 调用（约第 37 行）：

```python
    task_id = await service.create_article_task_with_quota_check(
        request.topic,
        current_user,
        style,
        request.enabled_image_methods,
        request.language,   # 新增
    )
```

- [ ] **Step 7: 运行现有测试确认无破坏**

```
cd python-backend
pytest tests/ -v --ignore=tests/test_i18n_schema.py
```
期望：所有原有测试仍然 PASS

- [ ] **Step 8: Commit**

```
git add app/services/article/article_service.py app/services/article/article_async_service.py app/routers/article.py
git commit -m "feat(i18n): wire language through service layer and async phases"
```

---

## Task 3: 后端 — PromptConstant 英文变体 + 分发方法

**Files:**
- Modify: `python-backend/app/constants/prompt.py`
- Create: `python-backend/tests/test_prompt_constant.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_prompt_constant.py
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
    assert "Title" in result or "title" in result


def test_get_falls_back_to_zh_when_en_missing():
    # AGENT5_IMAGE_EXECUTION_PROMPT 没有 _EN 变体，应回退中文
    result = PromptConstant.get("AGENT5_IMAGE_EXECUTION_PROMPT", "en")
    assert result == PromptConstant.AGENT5_IMAGE_EXECUTION_PROMPT


def test_get_style_instruction_zh():
    result = PromptConstant.get_style_instruction("POPULAR", "zh")
    assert "爆款" in result


def test_get_style_instruction_en():
    result = PromptConstant.get_style_instruction("POPULAR", "en")
    assert result  # 不为空
    assert "爆款" not in result  # 不是中文版


def test_get_style_instruction_unknown_style():
    result = PromptConstant.get_style_instruction("UNKNOWN", "en")
    assert result == ""


def test_all_en_variants_exist():
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
```

- [ ] **Step 2: 运行测试确认失败**

```
cd python-backend
pytest tests/test_prompt_constant.py -v
```
期望：FAIL — `get` 方法不存在

- [ ] **Step 3: 在 `app/constants/prompt.py` 末尾添加所有内容**

在文件末尾（`get_style_instruction` 方法之后），替换 `get_style_instruction` 并追加以下全部内容：

```python
    # ─── 英文变体 ────────────────────────────────────────────────────────────

    AGENT1_TITLE_PROMPT_EN = """You are an expert headline writer specializing in attention-grabbing titles. {styleInstruction}

Based on the following topic, generate 3-5 viral article title options:
Topic: {topic}

Requirements:
1. Each option includes a main title and a sub title
2. Main titles should include numbers, emotional words, and be eye-catching
3. Sub titles should supplement and enhance appeal
4. Titles should be concise and powerful, under 30 words
5. Different options should approach from different angles
6. Title style should match the writing style requirements above

Please return JSON format directly, no other content:
[
  {
    "mainTitle": "Main Title 1",
    "subTitle": "Sub Title 1"
  },
  {
    "mainTitle": "Main Title 2",
    "subTitle": "Sub Title 2"
  },
  {
    "mainTitle": "Main Title 3",
    "subTitle": "Sub Title 3"
  }
]
"""

    AGENT2_DESCRIPTION_SECTION_EN = """
User additional requirements: {userDescription}
Please fully incorporate the user's requirements in the outline.
"""

    AGENT2_OUTLINE_PROMPT_EN = """You are a professional article strategist specializing in designing article structures. {styleInstruction}

Based on the following title, generate an article outline:
Main Title: {mainTitle}
Sub Title: {subTitle}
{descriptionSection}
Requirements:
1. The outline should have a clear logical structure
2. Include an introduction, core arguments (3-5), and a closing conclusion
3. Each section should have a clear title and key points (2-3 per section)
4. Suitable for an article of approximately 2000 words
5. Section title wording should match the writing style above

Please return JSON format directly, no other content:
{
  "sections": [
    {
      "section": 1,
      "title": "Section Title",
      "points": ["Point 1", "Point 2"]
    }
  ]
}
"""

    AGENT3_CONTENT_PROMPT_EN = """You are a senior content creator specializing in writing high-quality articles. {styleInstruction}

Based on the following outline, write the article body:
Main Title: {mainTitle}
Sub Title: {subTitle}
Outline:
{outline}

Requirements:
1. Content should be rich, 300-400 words per section
2. Language should be fluent and engaging
3. Use impactful quotes to enhance readability
4. Add transition sentences to ensure logical flow
5. Use Markdown format, sections use ## headings

Please return Markdown formatted body content directly, no other content.
"""

    AGENT4_IMAGE_REQUIREMENTS_PROMPT_EN = """You are a professional new media editor specializing in selecting images for articles.

Based on the following article content, analyze image requirements and select the most suitable image method for each position:
Main Title: {mainTitle}
Body:
{content}

Available image method descriptions:
- PEXELS: Suitable for real scenes, people, landscapes, business scenes and other realistic images
- NANO_BANANA: Suitable for creative illustrations, artistic styles, abstract concept images
- MERMAID: Suitable for flowcharts, architecture diagrams, sequence diagrams, step instructions, comparison relationships, logical structures
- ICONIFY: Suitable for icons with text descriptions, symbol markers, simple lists
- EMOJI_PACK: Suitable for light-hearted humor, emotional expression, entertainment content

Requirements:
1. Identify positions that need images (cover, key sections, etc.)
2. Recommended image count: 3-5 images
3. Intelligently select the most suitable image method based on section content
4. Generate English search keywords for each image position
5. sectionTitle must exactly match the section title in the body (used to locate insertion position)
6. position=1 is the cover image, leave sectionTitle empty

Please return JSON format directly, no other content:
[
  {
    "position": 1,
    "type": "cover",
    "sectionTitle": "",
    "keywords": "AI technology office modern",
    "imageMethod": "PEXELS"
  },
  {
    "position": 2,
    "type": "section",
    "sectionTitle": "Section Title (exactly matching body)",
    "keywords": "workflow process diagram",
    "imageMethod": "MERMAID"
  }
]
"""

    AI_MODIFY_OUTLINE_PROMPT_EN = """You are a professional article strategist specializing in optimizing article structures based on user feedback.

Current article information:
Main Title: {mainTitle}
Sub Title: {subTitle}

Current outline:
{currentOutline}

User modification suggestions:
{modifySuggestion}

Requirements:
1. Adjust the outline structure according to the user's modification suggestions
2. Maintain the logical coherence and completeness of the outline
3. If the user suggests deleting a section, delete it; if adding, add it; if modifying, modify it
4. Maintain the JSON format unchanged
5. Section numbers are automatically re-ordered

Please return the modified outline in JSON format directly, no other content:
{
  "sections": [
    {
      "section": 1,
      "title": "Section Title",
      "points": ["Point 1", "Point 2"]
    }
  ]
}
"""

    # 文章风格指令映射（英文版）
    STYLE_INSTRUCTIONS_EN = {
        "POPULAR": "\nWriting style: Viral social media style, accessible language, use of parallelism and memorable quotes, emotional expression that resonates with readers.",
        "PROFESSIONAL": "\nWriting style: Professional in-depth style, rigorous logic, data-driven, clear viewpoints, suitable for professional readers.",
        "HUMOROUS": "\nWriting style: Light and humorous style, use metaphors and humor, lively and interesting language, let readers gain knowledge while laughing.",
        "STORYTELLING": "\nWriting style: Narrative storytelling style, centered on specific cases and stories, vivid plot, strong sense of immersion.",
    }

    # ─── 分发方法 ─────────────────────────────────────────────────────────────

    @staticmethod
    def get(name: str, language: str = 'zh') -> str:
        """按语言取 Prompt，英文版缺失时回退中文。"""
        if language == 'en':
            return getattr(PromptConstant, f"{name}_EN",
                           getattr(PromptConstant, name))
        return getattr(PromptConstant, name)

    @staticmethod
    def get_style_instruction(style: str, language: str = 'zh') -> str:
        """按语言取风格指令，英文版缺失时回退空字符串。"""
        instructions = (PromptConstant.STYLE_INSTRUCTIONS_EN
                        if language == 'en'
                        else PromptConstant.STYLE_INSTRUCTIONS)
        return instructions.get(style, "")
```

**注意：** 同时删除原来的 `get_style_instruction` `@classmethod`（最后几行），用上面的 `@staticmethod` 版本替换。

- [ ] **Step 4: 运行测试确认通过**

```
cd python-backend
pytest tests/test_prompt_constant.py -v
```
期望：8 tests PASS

- [ ] **Step 5: Commit**

```
git add app/constants/prompt.py tests/test_prompt_constant.py
git commit -m "feat(i18n): add English prompt variants and PromptConstant.get() dispatch method"
```

---

## Task 4: 后端 — ArticleAgentService 使用 PromptConstant.get()

**Files:**
- Modify: `python-backend/app/services/article/article_agent_service.py`

- [ ] **Step 1: 更新 `agent1_generate_title_options`（约第 92 行）**

将：
```python
        style_instruction = PromptConstant.get_style_instruction(state.style)
        prompt = (
            PromptConstant.AGENT1_TITLE_PROMPT
            .replace("{topic}", state.topic)
            .replace("{styleInstruction}", style_instruction)
        )
```

改为：
```python
        style_instruction = PromptConstant.get_style_instruction(state.style, state.language)
        prompt = (
            PromptConstant.get("AGENT1_TITLE_PROMPT", state.language)
            .replace("{topic}", state.topic)
            .replace("{styleInstruction}", style_instruction)
        )
```

- [ ] **Step 2: 更新 `agent2_generate_outline`（约第 114 行）**

将：
```python
        description_section = ""
        if state.user_description and state.user_description.strip():
            description_section = PromptConstant.AGENT2_DESCRIPTION_SECTION.replace(
                "{userDescription}", state.user_description
            )

        style_instruction = PromptConstant.get_style_instruction(state.style)
        prompt = (
            PromptConstant.AGENT2_OUTLINE_PROMPT
            .replace("{mainTitle}", state.title.main_title)
            .replace("{subTitle}", state.title.sub_title)
            .replace("{descriptionSection}", description_section)
            .replace("{styleInstruction}", style_instruction)
        )
```

改为：
```python
        description_section = ""
        if state.user_description and state.user_description.strip():
            description_section = PromptConstant.get("AGENT2_DESCRIPTION_SECTION", state.language).replace(
                "{userDescription}", state.user_description
            )

        style_instruction = PromptConstant.get_style_instruction(state.style, state.language)
        prompt = (
            PromptConstant.get("AGENT2_OUTLINE_PROMPT", state.language)
            .replace("{mainTitle}", state.title.main_title)
            .replace("{subTitle}", state.title.sub_title)
            .replace("{descriptionSection}", description_section)
            .replace("{styleInstruction}", style_instruction)
        )
```

- [ ] **Step 3: 更新 `agent3_generate_content`（约第 155 行）**

将：
```python
        style_instruction = PromptConstant.get_style_instruction(state.style)
        prompt = (
            PromptConstant.AGENT3_CONTENT_PROMPT
            .replace("{styleInstruction}", style_instruction)
            .replace("{mainTitle}", state.title.main_title)
            .replace("{subTitle}", state.title.sub_title)
            .replace("{outline}", outline_text)
        )
```

改为：
```python
        style_instruction = PromptConstant.get_style_instruction(state.style, state.language)
        prompt = (
            PromptConstant.get("AGENT3_CONTENT_PROMPT", state.language)
            .replace("{styleInstruction}", style_instruction)
            .replace("{mainTitle}", state.title.main_title)
            .replace("{subTitle}", state.title.sub_title)
            .replace("{outline}", outline_text)
        )
```

- [ ] **Step 4: 更新 `agent4_analyze_image_requirements`（约第 181 行）**

将：
```python
        prompt = (
            PromptConstant.AGENT4_IMAGE_REQUIREMENTS_PROMPT
            .replace("{mainTitle}", state.title.main_title)
            .replace("{content}", state.content)
        )
```

改为：
```python
        prompt = (
            PromptConstant.get("AGENT4_IMAGE_REQUIREMENTS_PROMPT", state.language)
            .replace("{mainTitle}", state.title.main_title)
            .replace("{content}", state.content)
        )
```

- [ ] **Step 5: 更新 `ai_modify_outline` — 添加 language 参数并使用 get()**

方法签名（约第 259 行）改为：

```python
    async def ai_modify_outline(
        self,
        main_title: str,
        sub_title: str,
        current_outline: List[OutlineSection],
        modify_suggestion: str,
        task_id: Optional[str] = None,
        language: str = 'zh',   # 新增
    ) -> List[OutlineSection]:
```

prompt 构建改为：
```python
        prompt = (
            PromptConstant.get("AI_MODIFY_OUTLINE_PROMPT", language)
            .replace("{mainTitle}", main_title)
            .replace("{subTitle}", sub_title)
            .replace("{currentOutline}", current_outline_json)
            .replace("{modifySuggestion}", modify_suggestion)
        )
```

- [ ] **Step 6: 运行所有后端测试**

```
cd python-backend
pytest tests/ -v
```
期望：所有测试 PASS（约 30+ tests）

- [ ] **Step 7: Commit**

```
git add app/services/article/article_agent_service.py
git commit -m "feat(i18n): update ArticleAgentService to use PromptConstant.get() for bilingual prompts"
```

---

## Task 5: 前端 — vue-i18n 安装 + locale 文件 + plugin

**Files:**
- Install: `vue-i18n@9`
- Create: `vue-frontend/src/locales/zh.ts`
- Create: `vue-frontend/src/locales/en.ts`
- Create: `vue-frontend/src/plugins/i18n.ts`
- Modify: `vue-frontend/src/main.ts`

- [ ] **Step 1: 安装 vue-i18n**

```
cd vue-frontend
npm install vue-i18n@9
```

期望：`package.json` 中出现 `"vue-i18n": "^9.x.x"`

- [ ] **Step 2: 创建 `src/locales/zh.ts`**

```typescript
// src/locales/zh.ts
export default {
  nav: {
    articles: '文章列表',
    vip: '会员中心',
    stats: '统计',
    logout: '退出登录',
    upgradeVip: '升级 VIP',
  },
  auth: {
    account: '账号',
    password: '密码',
    login: '登录',
    register: '注册',
    noAccount: '没有账号？',
    hasAccount: '已有账号？',
    loginBtn: '登录',
    registerBtn: '注册',
    loginSuccess: '登录成功',
    logoutSuccess: '已退出登录',
    accountPlaceholder: '请输入账号',
    passwordPlaceholder: '请输入密码',
    accountRequired: '请输入账号',
    accountMinLength: '账号不能少于4位',
    passwordRequired: '请输入密码',
    passwordMinLength: '密码不能少于8位',
  },
  home: {
    title: 'AI 爆款文章创作器',
  },
  article: {
    create: {
      settings: '创作设置',
      topicLabel: '文章选题',
      topicPlaceholder: '请输入文章选题，例如：年轻人如何在大城市低成本生活',
      styleLabel: '文章风格',
      imageMethodsLabel: '配图方式',
      quotaAlert: '免费用户最多创作 5 篇文章',
      upgradeVip: '升级 VIP →',
      generating: '生成中...',
      startBtn: '开始创作',
      restartBtn: '重新创作',
      taskId: '任务 ID',
      styles: {
        POPULAR: '爆款新媒体',
        PROFESSIONAL: '专业深度',
        HUMOROUS: '轻松幽默',
        STORYTELLING: '故事叙述',
      },
      imageMethodLabels: {
        PEXELS: 'Pexels 图库',
        PICSUM: 'Picsum 随机',
        NANO_BANANA: 'AI 生图',
        MERMAID: 'Mermaid 图',
        ICONIFY: '图标',
        EMOJI_PACK: '表情包',
        SVG_DIAGRAM: 'SVG 图',
      },
      phases: {
        TITLE_GENERATING: '生成标题方案',
        TITLE_SELECTING: '选择标题',
        OUTLINE_GENERATING: '生成大纲',
        OUTLINE_EDITING: '编辑大纲',
        CONTENT_GENERATING: '生成正文',
        COMPLETED: '创作完成',
      },
      phaseTitle: {
        INPUT: '文章预览',
        TITLE_GENERATING: '标题生成中',
        TITLE_SELECTING: '选择标题',
        OUTLINE_GENERATING: '大纲生成中',
        OUTLINE_EDITING: '编辑大纲',
        CONTENT_GENERATING: '正文生成中',
        COMPLETED: '文章预览',
      },
      progress: '生成进度',
      titleGenerating: 'AI 正在生成标题方案...',
      titleGeneratingDesc: '稍等片刻，即将为您呈现多个精彩标题',
      outlineGenerating: 'AI 正在规划文章大纲...',
      contentEmpty: '文章内容将在这里显示',
      contentGenerating: '正在生成正文...',
      noLogs: '点击「开始创作」启动生成',
      waitingConnection: '等待连接...',
      vipOnly: '该配图方式为 VIP 专属，请先升级',
      viewDetail: '查看详情',
    },
    titleSelect: {
      title: '选择标题方案',
      subtitle: 'AI 为您生成了以下标题，请选择一个或自定义',
      custom: '自定义标题',
      customMainTitle: '输入主标题',
      customSubTitle: '输入副标题',
      descLabel: '补充描述（可选）',
      descTip: '补充您对文章的期望、重点强调的内容等，AI 会在生成大纲时参考',
      descPlaceholder: '例如：请重点强调技术原理，用通俗的语言讲解...',
      confirmBtn: '确认并生成大纲',
    },
    outlineEdit: {
      title: '编辑文章大纲',
      subtitle: '可编辑章节内容、拖拽排序、添加/删除章节，或让 AI 辅助修改',
      sectionTitle: '章节标题',
      pointContent: '要点内容',
      addPoint: '+ 添加要点',
      aiAssistant: '🤖 AI 助手修改大纲',
      aiPlaceholder: '告诉 AI 如何修改大纲，例如：请在第二章节后增加一个关于实践案例的章节',
      aiModifyBtn: 'AI 修改',
      addSection: '+ 添加章节',
      confirmBtn: '确认并生成正文',
      aiSuccess: 'AI 已根据您的建议修改大纲',
      aiFailed: 'AI 修改失败',
    },
    list: {
      title: '我的文章',
      newBtn: '创作新文章',
      searchPlaceholder: '搜索选题关键词',
      allStatus: '全部状态',
      searchBtn: '搜索',
      total: '共 {total} 篇',
      status: {
        PENDING: '排队中',
        PROCESSING: '生成中',
        COMPLETED: '已完成',
        FAILED: '失败',
      },
    },
    detail: {
      status: '状态',
      topic: '选题',
      mainTitle: '主标题',
      subTitle: '副标题',
      createTime: '创建时间',
      completedTime: '完成时间',
      exportMd: '导出 Markdown',
      back: '返回',
      coverImg: '封面图',
    },
  },
  vip: {
    title: '升级 VIP 会员',
    subtitle: '解锁全部 AI 创作能力，无限创作精彩内容',
    alreadyVip: '您已是 VIP 会员',
    startCreate: '开始创作',
  },
  stats: {
    title: '智能体统计',
  },
  common: {
    loading: '加载中...',
    error: '出现错误，请重试',
  },
}
```

- [ ] **Step 3: 创建 `src/locales/en.ts`**

```typescript
// src/locales/en.ts
export default {
  nav: {
    articles: 'My Articles',
    vip: 'Membership',
    stats: 'Statistics',
    logout: 'Logout',
    upgradeVip: 'Upgrade VIP',
  },
  auth: {
    account: 'Account',
    password: 'Password',
    login: 'Login',
    register: 'Register',
    noAccount: "Don't have an account?",
    hasAccount: 'Already have an account?',
    loginBtn: 'Login',
    registerBtn: 'Register',
    loginSuccess: 'Login successful',
    logoutSuccess: 'Logged out successfully',
    accountPlaceholder: 'Enter your account',
    passwordPlaceholder: 'Enter your password',
    accountRequired: 'Please enter your account',
    accountMinLength: 'Account must be at least 4 characters',
    passwordRequired: 'Please enter your password',
    passwordMinLength: 'Password must be at least 8 characters',
  },
  home: {
    title: 'AI Article Creator',
  },
  article: {
    create: {
      settings: 'Creation Settings',
      topicLabel: 'Article Topic',
      topicPlaceholder: 'Enter the article topic, e.g.: How to live cost-effectively in big cities',
      styleLabel: 'Writing Style',
      imageMethodsLabel: 'Image Methods',
      quotaAlert: 'Free users can create up to 5 articles',
      upgradeVip: 'Upgrade VIP →',
      generating: 'Generating...',
      startBtn: 'Start Creating',
      restartBtn: 'Start Over',
      taskId: 'Task ID',
      styles: {
        POPULAR: 'Viral Media',
        PROFESSIONAL: 'Professional',
        HUMOROUS: 'Humorous',
        STORYTELLING: 'Storytelling',
      },
      imageMethodLabels: {
        PEXELS: 'Pexels Photos',
        PICSUM: 'Random Photos',
        NANO_BANANA: 'AI Generated',
        MERMAID: 'Mermaid Diagram',
        ICONIFY: 'Icons',
        EMOJI_PACK: 'Emoji Pack',
        SVG_DIAGRAM: 'SVG Diagram',
      },
      phases: {
        TITLE_GENERATING: 'Generating Titles',
        TITLE_SELECTING: 'Select Title',
        OUTLINE_GENERATING: 'Generating Outline',
        OUTLINE_EDITING: 'Edit Outline',
        CONTENT_GENERATING: 'Generating Content',
        COMPLETED: 'Completed',
      },
      phaseTitle: {
        INPUT: 'Article Preview',
        TITLE_GENERATING: 'Generating Titles',
        TITLE_SELECTING: 'Select Title',
        OUTLINE_GENERATING: 'Generating Outline',
        OUTLINE_EDITING: 'Edit Outline',
        CONTENT_GENERATING: 'Generating Content',
        COMPLETED: 'Article Preview',
      },
      progress: 'Generation Progress',
      titleGenerating: 'AI is generating title options...',
      titleGeneratingDesc: 'Please wait, multiple title options are coming up',
      outlineGenerating: 'AI is planning the article outline...',
      contentEmpty: 'Article content will appear here',
      contentGenerating: 'Generating content...',
      noLogs: 'Click "Start Creating" to begin',
      waitingConnection: 'Waiting for connection...',
      vipOnly: 'This image method is VIP exclusive, please upgrade first',
      viewDetail: 'View Details',
    },
    titleSelect: {
      title: 'Select a Title',
      subtitle: 'AI has generated the following titles, please select one or customize',
      custom: 'Custom Title',
      customMainTitle: 'Enter main title',
      customSubTitle: 'Enter sub title',
      descLabel: 'Additional Description (Optional)',
      descTip: 'Add your expectations and key points, AI will reference them when generating the outline',
      descPlaceholder: 'e.g.: Please emphasize technical principles in plain language...',
      confirmBtn: 'Confirm & Generate Outline',
    },
    outlineEdit: {
      title: 'Edit Article Outline',
      subtitle: 'Edit sections, drag to reorder, add/delete sections, or use AI to assist',
      sectionTitle: 'Section Title',
      pointContent: 'Key Point',
      addPoint: '+ Add Point',
      aiAssistant: '🤖 AI Outline Assistant',
      aiPlaceholder: 'Tell AI how to modify the outline, e.g.: Add a practical case section after section 2',
      aiModifyBtn: 'AI Modify',
      addSection: '+ Add Section',
      confirmBtn: 'Confirm & Generate Content',
      aiSuccess: 'AI has modified the outline based on your feedback',
      aiFailed: 'AI modification failed',
    },
    list: {
      title: 'My Articles',
      newBtn: 'New Article',
      searchPlaceholder: 'Search topics',
      allStatus: 'All Status',
      searchBtn: 'Search',
      total: 'Total {total}',
      status: {
        PENDING: 'Queued',
        PROCESSING: 'Generating',
        COMPLETED: 'Completed',
        FAILED: 'Failed',
      },
    },
    detail: {
      status: 'Status',
      topic: 'Topic',
      mainTitle: 'Main Title',
      subTitle: 'Sub Title',
      createTime: 'Created At',
      completedTime: 'Completed At',
      exportMd: 'Export Markdown',
      back: 'Back',
      coverImg: 'Cover Image',
    },
  },
  vip: {
    title: 'Upgrade to VIP',
    subtitle: 'Unlock all AI creation capabilities, create unlimited content',
    alreadyVip: 'You are already a VIP member',
    startCreate: 'Start Creating',
  },
  stats: {
    title: 'Agent Statistics',
  },
  common: {
    loading: 'Loading...',
    error: 'An error occurred, please try again',
  },
}
```

- [ ] **Step 4: 创建 `src/plugins/i18n.ts`**

```typescript
// src/plugins/i18n.ts
import { createI18n } from 'vue-i18n'
import zh from '@/locales/zh'
import en from '@/locales/en'

const savedLang = localStorage.getItem('lang') ?? 'zh'

const i18n = createI18n({
  legacy: false,        // 使用 Composition API 模式
  locale: savedLang,
  fallbackLocale: 'zh',
  messages: { zh, en },
})

export default i18n
```

- [ ] **Step 5: 修改 `src/main.ts` — 注册 i18n**

```typescript
import './assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import i18n from './plugins/i18n'   // 新增

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(i18n)   // 新增

app.mount('#app')
```

- [ ] **Step 6: 验证编译无错误**

```
cd vue-frontend
npm run build
```
期望：build 成功，无 TypeScript 错误

- [ ] **Step 7: Commit**

```
git add vue-frontend/src/locales/ vue-frontend/src/plugins/i18n.ts vue-frontend/src/main.ts vue-frontend/package.json vue-frontend/package-lock.json
git commit -m "feat(i18n): install vue-i18n, create zh/en locales and i18n plugin"
```

---

## Task 6: 前端 — AppHeader 语言切换 + api/article.ts 联动

**Files:**
- Modify: `vue-frontend/src/components/AppHeader.vue`
- Modify: `vue-frontend/src/api/article.ts`

- [ ] **Step 1: 修改 `AppHeader.vue` — 添加语言切换 + 国际化**

用以下内容完整替换 `AppHeader.vue`：

```vue
<template>
  <a-layout-header class="app-header">
    <span class="logo" @click="router.push('/')">{{ $t('home.title') }}</span>
    <a-space>
      <a-button type="link" style="color:#fff" @click="router.push('/article/list')">
        {{ $t('nav.articles') }}
      </a-button>
      <a-button
        v-if="userStore.isAdmin"
        type="link"
        style="color:#fff"
        @click="router.push('/admin/statistics')"
      >
        {{ $t('nav.stats') }}
      </a-button>
      <a-button
        v-if="!userStore.isVip"
        type="default"
        size="small"
        class="upgrade-btn"
        @click="router.push('/vip')"
      >
        {{ $t('nav.upgradeVip') }}
      </a-button>
      <a-tag v-else color="gold" class="vip-badge">VIP</a-tag>

      <!-- 语言切换 -->
      <div class="lang-switcher">
        <span
          :class="['lang-btn', { active: locale === 'zh' }]"
          @click="switchLang('zh')"
        >ZH</span>
        <span class="lang-sep">|</span>
        <span
          :class="['lang-btn', { active: locale === 'en' }]"
          @click="switchLang('en')"
        >EN</span>
      </div>

      <a-dropdown>
        <a-space style="color:#fff;cursor:pointer">
          <a-avatar>{{ userStore.userInfo?.userName?.charAt(0) ?? 'U' }}</a-avatar>
          <span>{{ userStore.userInfo?.userName }}</span>
        </a-space>
        <template #overlay>
          <a-menu>
            <a-menu-item @click="router.push('/vip')">{{ $t('nav.vip') }}</a-menu-item>
            <a-menu-divider />
            <a-menu-item @click="onLogout">{{ $t('nav.logout') }}</a-menu-item>
          </a-menu>
        </template>
      </a-dropdown>
    </a-space>
  </a-layout-header>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { userLogout } from '@/api/user'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()
const { locale } = useI18n()

function switchLang(lang: string) {
  locale.value = lang
  localStorage.setItem('lang', lang)
}

async function onLogout() {
  await userLogout()
  userStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: #001529;
  position: sticky;
  top: 0;
  z-index: 100;
}

.logo {
  color: #fff;
  font-size: 18px;
  font-weight: 700;
  cursor: pointer;
}

.upgrade-btn {
  background: linear-gradient(135deg, #faad14, #fa8c16);
  border: none;
  color: #fff;
  font-weight: 600;
  border-radius: 4px;
}

.upgrade-btn:hover {
  opacity: 0.85;
}

.vip-badge {
  font-weight: 700;
  font-size: 13px;
}

.lang-switcher {
  display: flex;
  align-items: center;
  gap: 2px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  padding: 2px 8px;
}

.lang-btn {
  color: rgba(255, 255, 255, 0.6);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  padding: 0 2px;
  transition: color 0.2s;
  user-select: none;
}

.lang-btn:hover {
  color: #fff;
}

.lang-btn.active {
  color: #fff;
}

.lang-sep {
  color: rgba(255, 255, 255, 0.3);
  font-size: 11px;
}
</style>
```

- [ ] **Step 2: 修改 `src/api/article.ts` — ArticleCreateRequest + createArticle 联动 language**

在 `ArticleCreateRequest` interface 添加 `language` 字段（约第 36 行）：

```typescript
export interface ArticleCreateRequest {
  topic: string
  style?: string
  enabledImageMethods?: string[]
  language?: string   // 新增
}
```

更新 `createArticle` 函数自动注入当前语言（约第 59 行）：

```typescript
import i18n from '@/plugins/i18n'

export function createArticle(params: ArticleCreateRequest) {
  const language = (i18n.global.locale as any).value ?? 'zh'
  return request.post<any, { data: string }>('/article/create', { ...params, language })
}
```

**注意：** `import i18n from '@/plugins/i18n'` 需要加在文件顶部 `import request` 之后。

- [ ] **Step 3: 手动验证**

1. 启动前后端
2. 切换到 EN，创建新文章
3. 检查后端日志：agent1 的 prompt 应为英文
4. 刷新页面，确认语言偏好保持为 EN
5. 切换回 ZH，新文章的 prompt 应为中文

- [ ] **Step 4: Commit**

```
git add vue-frontend/src/components/AppHeader.vue vue-frontend/src/api/article.ts
git commit -m "feat(i18n): add language switcher to AppHeader, wire language to createArticle"
```

---

## Task 7: 前端 — ArticleCreatePage + 子组件国际化

**Files:**
- Modify: `vue-frontend/src/views/article/ArticleCreatePage.vue`
- Modify: `vue-frontend/src/views/article/components/TitleSelectingStage.vue`
- Modify: `vue-frontend/src/views/article/components/OutlineEditingStage.vue`

- [ ] **Step 1: 修改 `ArticleCreatePage.vue` — Script 部分**

在 `<script setup>` 中添加 `useI18n`：

```typescript
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
```

将 `ARTICLE_STYLES` 的 `label` 改为用 `t()` 动态取（在 template 中）。

将 `IMAGE_METHODS` 改为不含中文 label 的版本（label 从 locale 取）：

```typescript
const IMAGE_METHODS = [
  { value: 'PEXELS', icon: '📷', vipOnly: false },
  { value: 'NANO_BANANA', icon: '🎨', vipOnly: true },
  { value: 'MERMAID', icon: '📊', vipOnly: false },
  { value: 'ICONIFY', icon: '🔷', vipOnly: false },
  { value: 'EMOJI_PACK', icon: '😄', vipOnly: false },
]
```

将 `PHASE_STEPS` 改为不含中文 label（label 从 locale 取）：

```typescript
const PHASE_STEPS = [
  { key: 'TITLE_GENERATING' },
  { key: 'TITLE_SELECTING' },
  { key: 'OUTLINE_GENERATING' },
  { key: 'OUTLINE_EDITING' },
  { key: 'CONTENT_GENERATING' },
  { key: 'COMPLETED' },
] as const
```

将 `rightPanelTitle` computed 改为：

```typescript
const rightPanelTitle = computed(() => t(`article.create.phaseTitle.${currentPhase.value}`))
```

将 `statusText` computed 改为：

```typescript
const statusText = computed(() => {
  const key = `article.list.status.${status.value}`
  return t(key, status.value)
})
```

将 `toggleImageMethod` 中的警告信息改为：

```typescript
message.warning(t('article.create.vipOnly'))
```

- [ ] **Step 2: 修改 `ArticleCreatePage.vue` — Template 部分**

替换所有硬编码中文字符串为 `t()` 调用：

| 原文 | 替换为 |
|------|--------|
| `title="创作设置"` | `:title="t('article.create.settings')"` |
| `label="文章选题"` | `:label="t('article.create.topicLabel')"` |
| `placeholder="请输入文章选题..."` | `:placeholder="t('article.create.topicPlaceholder')"` |
| `label="文章风格"` | `:label="t('article.create.styleLabel')"` |
| `label="配图方式"` | `:label="t('article.create.imageMethodsLabel')"` |
| `{{ s.label }}` | `{{ t('article.create.styles.' + s.value) }}` |
| `{{ m.label }}` | `{{ t('article.create.imageMethodLabels.' + m.value) }}` |
| `免费用户最多创作 5 篇文章` | `{{ t('article.create.quotaAlert') }}` |
| `升级 VIP →` | `{{ t('article.create.upgradeVip') }}` |
| `{{ isCreating ? '生成中...' : '开始创作' }}` | `{{ isCreating ? t('article.create.generating') : t('article.create.startBtn') }}` |
| `重新创作` | `{{ t('article.create.restartBtn') }}` |
| `任务 ID：` | `{{ t('article.create.taskId') }}：` |
| `{{ step.label }}` | `{{ t('article.create.phases.' + step.key) }}` |
| `title="生成进度"` | `:title="t('article.create.progress')"` |
| `等待连接...` | `{{ t('article.create.waitingConnection') }}` |
| `点击「开始创作」启动生成` | `{{ t('article.create.noLogs') }}` |
| `AI 正在生成标题方案...` | `{{ t('article.create.titleGenerating') }}` |
| `稍等片刻，即将为您呈现多个精彩标题` | `{{ t('article.create.titleGeneratingDesc') }}` |
| `AI 正在规划文章大纲...` | `{{ t('article.create.outlineGenerating') }}` |
| `正在生成正文...` | `{{ t('article.create.contentGenerating') }}` |
| `description="文章内容将在这里显示"` | `:description="t('article.create.contentEmpty')"` |
| `查看详情` | `{{ t('article.create.viewDetail') }}` |
| `{{ IMAGE_METHOD_LABELS[log.method] ?? log.method }}` | `{{ t('article.create.imageMethodLabels.' + log.method, log.method) }}` |

另外移除 `IMAGE_METHOD_LABELS` 的导入（改用 t()），同时 `ARTICLE_STYLES` 仍需导入（用于 icon 和 value），但 `label` 不再使用。

- [ ] **Step 3: 修改 `TitleSelectingStage.vue`**

在 `<script setup>` 添加：
```typescript
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
```

替换 template 中所有中文：

| 原文 | 替换为 |
|------|--------|
| `选择标题方案` | `{{ t('article.titleSelect.title') }}` |
| `AI 为您生成了以下标题，请选择一个或自定义` | `{{ t('article.titleSelect.subtitle') }}` |
| `自定义标题` | `{{ t('article.titleSelect.custom') }}` |
| `placeholder="输入主标题"` | `:placeholder="t('article.titleSelect.customMainTitle')"` |
| `placeholder="输入副标题"` | `:placeholder="t('article.titleSelect.customSubTitle')"` |
| `补充描述（可选）` | `{{ t('article.titleSelect.descLabel') }}` |
| `补充您对文章的期望...` | `{{ t('article.titleSelect.descTip') }}` |
| `placeholder="例如：请重点强调技术原理..."` | `:placeholder="t('article.titleSelect.descPlaceholder')"` |
| `确认并生成大纲` | `{{ t('article.titleSelect.confirmBtn') }}` |

- [ ] **Step 4: 修改 `OutlineEditingStage.vue`**

在 `<script setup>` 添加：
```typescript
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
```

更新 `message.success/error` 调用：
```typescript
message.success(t('article.outlineEdit.aiSuccess'))
// ...
message.error(err?.message || t('article.outlineEdit.aiFailed'))
```

替换 template 中所有中文：

| 原文 | 替换为 |
|------|--------|
| `编辑文章大纲` | `{{ t('article.outlineEdit.title') }}` |
| `可编辑章节内容...` | `{{ t('article.outlineEdit.subtitle') }}` |
| `placeholder="章节标题"` | `:placeholder="t('article.outlineEdit.sectionTitle')"` |
| `placeholder="要点内容"` | `:placeholder="t('article.outlineEdit.pointContent')"` |
| `+ 添加要点` | `{{ t('article.outlineEdit.addPoint') }}` |
| `🤖 AI 助手修改大纲` | `{{ t('article.outlineEdit.aiAssistant') }}` |
| `placeholder="告诉 AI 如何修改大纲..."` | `:placeholder="t('article.outlineEdit.aiPlaceholder')"` |
| `AI 修改` | `{{ t('article.outlineEdit.aiModifyBtn') }}` |
| `+ 添加章节` | `{{ t('article.outlineEdit.addSection') }}` |
| `确认并生成正文` | `{{ t('article.outlineEdit.confirmBtn') }}` |

- [ ] **Step 5: 验证**

在浏览器中切换 ZH/EN，进入创作页面，确认：
- 所有标签、按钮、placeholder 随语言切换
- 阶段步骤名称随语言切换
- 标题选择、大纲编辑组件文字随语言切换

- [ ] **Step 6: Commit**

```
git add vue-frontend/src/views/article/ArticleCreatePage.vue vue-frontend/src/views/article/components/
git commit -m "feat(i18n): internationalize ArticleCreatePage and article sub-components"
```

---

## Task 8: 前端 — 其余页面国际化

**Files:**
- Modify: `vue-frontend/src/views/LoginView.vue`
- Modify: `vue-frontend/src/views/RegisterView.vue`
- Modify: `vue-frontend/src/views/VipPage.vue`
- Modify: `vue-frontend/src/views/article/ArticleListPage.vue`
- Modify: `vue-frontend/src/views/article/ArticleDetailPage.vue`
- Modify: `vue-frontend/src/views/admin/StatisticsPage.vue`

- [ ] **Step 1: 修改 `LoginView.vue`**

在 `<script setup>` 添加：
```typescript
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
```

替换 template 中的硬编码文字：

```vue
<a-card :title="t('auth.login')" class="auth-card">
  <a-form :model="form" layout="vertical" @finish="onFinish">
    <a-form-item
      :label="t('auth.account')"
      name="userAccount"
      :rules="[
        { required: true, message: t('auth.accountRequired') },
        { min: 4, message: t('auth.accountMinLength') }
      ]"
    >
      <a-input v-model:value="form.userAccount" :placeholder="t('auth.accountPlaceholder')" />
    </a-form-item>
    <a-form-item
      :label="t('auth.password')"
      name="userPassword"
      :rules="[
        { required: true, message: t('auth.passwordRequired') },
        { min: 8, message: t('auth.passwordMinLength') }
      ]"
    >
      <a-input-password v-model:value="form.userPassword" :placeholder="t('auth.passwordPlaceholder')" />
    </a-form-item>
    <a-form-item>
      <a-button type="primary" html-type="submit" :loading="loading" block>{{ t('auth.loginBtn') }}</a-button>
    </a-form-item>
    <div class="auth-link">
      {{ t('auth.noAccount') }}<router-link to="/register">{{ t('auth.register') }}</router-link>
    </div>
  </a-form>
</a-card>
```

同时在 `message.success('登录成功')` 处改为 `message.success(t('auth.loginSuccess'))`。

- [ ] **Step 2: 修改 `RegisterView.vue`**

先读取 `RegisterView.vue` 的内容，然后：
- 添加 `useI18n` 导入
- 将 `title="注册"` → `:title="t('auth.register')"`
- label、placeholder、rules message、button 文字等类似 LoginView.vue 的处理方式

读取文件：`src/views/RegisterView.vue`，然后按 LoginView.vue 相同模式替换所有中文文字。

- [ ] **Step 3: 修改 `VipPage.vue`**

添加 `useI18n` 导入，替换：
- `title="您已是 VIP 会员"` → `:title="t('vip.alreadyVip')"`
- `开始创作` → `{{ t('vip.startCreate') }}`
- `升级 VIP 会员` → `{{ t('vip.title') }}`
- `解锁全部 AI 创作能力...` → `{{ t('vip.subtitle') }}`

- [ ] **Step 4: 修改 `ArticleListPage.vue`**

添加 `useI18n` 导入，替换：
- 页面标题 `我的文章` → `{{ t('article.list.title') }}`
- 按钮 `创作新文章` → `{{ t('article.list.newBtn') }}`
- `placeholder="搜索选题关键词"` → `:placeholder="t('article.list.searchPlaceholder')"`
- `placeholder="全部状态"` → `:placeholder="t('article.list.allStatus')"`
- 搜索按钮 `搜索` → `{{ t('article.list.searchBtn') }}`
- 状态 tag 文字（PENDING/PROCESSING/COMPLETED/FAILED）→ `{{ t('article.list.status.' + record.status) }}`
- 分页 `showTotal: (total) => \`共 ${total} 篇\`` → `showTotal: (total) => t('article.list.total', { total })`
- 表头列名称按需替换

- [ ] **Step 5: 修改 `ArticleDetailPage.vue`**

添加 `useI18n` 导入，替换：
- 描述字段 label：`label="状态"` → `:label="t('article.detail.status')"`（以此类推）
- 按钮文字：`导出 Markdown` → `{{ t('article.detail.exportMd') }}`，`返回` → `{{ t('article.detail.back') }}`
- 封面图卡片标题 `封面图` → `{{ t('article.detail.coverImg') }}`
- `statusText` computed 中的映射改为 `t('article.list.status.' + article.status)`

- [ ] **Step 6: 修改 `StatisticsPage.vue`**

添加 `useI18n` 导入，替换页面标题 `智能体统计` → `{{ t('stats.title') }}`。其余统计图表数据标签（ECharts 配置中的中文字符串）暂不在 i18n 范围内，保持原样。

- [ ] **Step 7: 全页面验证**

切换语言到 EN，逐个检查：
- 登录页：所有表单文字为英文
- 注册页：所有表单文字为英文
- VIP 页：标题、副标题为英文
- 文章列表页：标题、按钮、状态 tag 为英文
- 文章详情页：描述项 label、按钮为英文
- 统计页：标题为英文

- [ ] **Step 8: Commit**

```
git add vue-frontend/src/views/
git commit -m "feat(i18n): internationalize remaining pages (login, register, vip, list, detail, stats)"
```

---

## 收尾验证

- [ ] 切换到 EN，创建一篇新文章 → 所有 agent 生成的内容（标题、大纲、正文）均为英文
- [ ] 切换回 ZH，新文章恢复中文生成
- [ ] 刷新浏览器，语言偏好保持
- [ ] `pytest tests/ -v` 全部通过
- [ ] `npm run build` 无错误

---

## 测试要点速查

| 场景 | 期望 |
|------|------|
| `ArticleCreateRequest(topic="test")` | `language == 'zh'` |
| `PromptConstant.get("AGENT1_TITLE_PROMPT", "en")` | 返回英文 prompt |
| `PromptConstant.get("AGENT5_IMAGE_EXECUTION_PROMPT", "en")` | 回退到中文 prompt |
| `get_style_instruction("POPULAR", "en")` | 返回英文 style 说明 |
| 前端 localStorage `lang=en` + 刷新 | 仍显示英文 UI |
| EN 模式创建文章后端日志 | agent1 prompt 为英文 |
