class PromptConstant:
    AGENT1_TITLE_PROMPT = """你是一位爆款文章标题专家,擅长创作吸引人的标题。{styleInstruction}

根据以下选题,生成 3-5 个爆款文章标题方案:
选题：{topic}

要求:
1. 每个方案包含主标题和副标题
2. 主标题要包含数字、情绪化词汇,吸引眼球
3. 副标题要补充说明,增强吸引力
4. 标题要简洁有力,不超过30字
5. 不同方案要有不同的切入角度
6. 标题风格要符合上述写作风格要求

请直接返回 JSON 格式,不要有其他内容:
[
  {
    "mainTitle": "主标题1",
    "subTitle": "副标题1"
  },
  {
    "mainTitle": "主标题2",
    "subTitle": "副标题2"
  },
  {
    "mainTitle": "主标题3",
    "subTitle": "副标题3"
  }
]
"""

    # 用户补充描述段落（Day5 新增），动态插入到 AGENT2 Prompt 中
    AGENT2_DESCRIPTION_SECTION = """
用户补充要求：{userDescription}
请在大纲中充分体现用户的补充要求。
"""

    AGENT2_OUTLINE_PROMPT = """你是一位专业的文章策划师，擅长设计文章结构。{styleInstruction}

根据以下标题，生成文章大纲：
主标题：{mainTitle}
副标题：{subTitle}
{descriptionSection}
要求：
1. 大纲要有清晰的逻辑结构
2. 包含开头引入、核心观点（3-5个）、结尾升华
3. 每个章节要有明确的标题和核心要点（2-3个）
4. 适合2000字左右的文章
5. 章节标题的措辞要符合上述写作风格

请直接返回 JSON 格式，不要有其他内容：
{
  "sections": [
    {
      "section": 1,
      "title": "章节标题",
      "points": ["要点1", "要点2"]
    }
  ]
}
"""

    AGENT3_CONTENT_PROMPT = """你是一位资深的内容创作者，擅长撰写优质文章。{styleInstruction}

根据以下大纲，创作文章正文：
主标题：{mainTitle}
副标题：{subTitle}
大纲：
{outline}

要求：
1. 内容要充实，每个章节300-400字
2. 语言流畅，富有感染力
3. 适当使用金句，增强可读性
4. 添加过渡句，确保逻辑连贯
5. 使用 Markdown 格式，章节使用 ## 标题

请直接返回 Markdown 格式的正文内容，不要有其他内容。
"""

    AGENT4_IMAGE_REQUIREMENTS_PROMPT = """你是一位专业的新媒体编辑，擅长为文章配图。

根据以下文章内容，分析配图需求并为每个位置选择最合适的配图方式：
主标题：{mainTitle}
正文：
{content}

可选配图方式说明：
- PEXELS：适合真实场景、人物、风景、商业场景等写实类图片
- NANO_BANANA：适合创意插画、艺术风格、抽象概念图
- MERMAID：适合流程图、架构图、时序图、步骤说明、对比关系、逻辑结构等需要图解的内容
- ICONIFY：适合图标配合文字说明、符号标记、简洁列表
- EMOJI_PACK：适合轻松幽默的氛围、情绪表达、娱乐向内容

要求：
1. 识别需要配图的位置（封面、关键章节等）
2. 建议配图数量：3-5张
3. 根据章节内容特点智能选择最合适的配图方式
4. 为每个配图位置生成英文搜索关键词
5. sectionTitle 必须与正文中的章节标题完全一致（用于定位插入位置）
6. position=1 为封面图，sectionTitle 留空

请直接返回 JSON 格式，不要有其他内容：
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
    "sectionTitle": "章节标题（与正文完全一致）",
    "keywords": "workflow process diagram",
    "imageMethod": "MERMAID"
  }
]
"""

    # AI 修改大纲 Prompt（Day5 新增）
    AI_MODIFY_OUTLINE_PROMPT = """你是一位专业的文章策划师,擅长根据用户反馈优化文章结构。

当前文章信息：
主标题：{mainTitle}
副标题：{subTitle}

当前大纲：
{currentOutline}

用户修改建议：
{modifySuggestion}

要求：
1. 根据用户的修改建议，调整大纲结构
2. 保持大纲的逻辑性和完整性
3. 如果用户建议删除某章节，则删除；建议增加则增加；建议修改则修改
4. 保持 JSON 格式不变
5. 章节序号自动重新排序

请直接返回修改后的 JSON 格式大纲，不要有其他内容：
{
  "sections": [
    {
      "section": 1,
      "title": "章节标题",
      "points": ["要点1", "要点2"]
    }
  ]
}
"""

    # Day 8：并行配图执行说明（用于日志与编排标识）
    AGENT5_IMAGE_EXECUTION_PROMPT = "并行执行配图生成，确保结果按 position 顺序回填。"

    # 文章风格指令映射
    STYLE_INSTRUCTIONS = {
        "POPULAR": "\n写作风格：爆款新媒体风格，语言接地气，善用排比和金句，情绪化表达，引发共鸣。",
        "PROFESSIONAL": "\n写作风格：专业深度风格，逻辑严谨，数据支撑，观点鲜明，适合专业读者。",
        "HUMOROUS": "\n写作风格：轻松幽默风格，善用比喻和梗，语言活泼有趣，让读者在笑声中获取信息。",
        "STORYTELLING": "\n写作风格：故事叙述风格，以具体案例和故事为主线，情节生动，代入感强。",
    }

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
        """按语言取风格指令。"""
        instructions = (PromptConstant.STYLE_INSTRUCTIONS_EN
                        if language == 'en'
                        else PromptConstant.STYLE_INSTRUCTIONS)
        return instructions.get(style, "")
