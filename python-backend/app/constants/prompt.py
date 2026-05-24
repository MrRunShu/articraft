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

    @classmethod
    def get_style_instruction(cls, style: str) -> str:
        return cls.STYLE_INSTRUCTIONS.get(style, "")
