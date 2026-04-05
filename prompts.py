# -*- coding: utf-8 -*-
"""
AI 模拟面试器 - 提示词模板
策略：JD 为主轴；简历/作品集为证据与缺口来源（非出题主轴）。
"""

# ===== 匹配分析：先拆 JD，再用简历/作品集作证据对齐 =====
MATCH_ANALYSIS_WITH_PORTFOLIO_PROMPT = """你是一位专业招聘顾问。**必须先基于岗位 JD 提炼考察主轴**，再把简历、作品集当作「能否证明胜任」的证据材料来分析。

【重要原则】
1) **JD 决定岗位要什么人、考什么能力**；简历与作品集只回答：有哪些支撑证据、哪些还缺证据。
2) 不要先把候选人经历盘点一遍再贴 JD；要先把 JD 要求说清楚，再逐条对照材料。

【简历全文/节选】
{resume_text}

【作品集全文/节选】
{portfolio_text}

【岗位描述 JD】
{jd_text}

请严格输出 JSON（不要输出其他说明文字）：
{{
  "job_title_guess": "从 JD 推测的岗位名称（简短）",
  "jd_decomposition": {{
    "core_responsibilities": ["JD 中明确的核心职责，逐条简短"],
    "must_have_capabilities": ["JD 必备能力/硬性要求"],
    "bonus_points": ["加分项/优先项"],
    "risk_or_skepticism_points": ["JD 中隐含或容易被面试官质疑的风险点、高压点"]
  }},
  "resume_as_evidence": {{
    "supports_jd": ["简历中能直接支撑上述 JD 要求的证据（能力/经历/结果）"],
    "gaps_or_weak_evidence": ["相对 JD 仍不足、需在面试中重点验证的缺口"]
  }},
  "portfolio_as_evidence": {{
    "supports_jd": ["作品集中能支撑 JD 的证据；若无作品集则填 []"],
    "gaps_or_weak_evidence": ["作品侧相对 JD 的不足或需追问点；若无则 []"]
  }},
  "skill_match": {{
    "matched_skills": ["与 JD 硬性技能匹配项"],
    "partially_matched": ["部分匹配"],
    "missing_skills": ["相对 JD 明显缺失"]
  }},
  "experience_match": {{
    "strengths": ["对胜任岗位有利的经历亮点"],
    "gaps": ["经历上与 JD 的落差"]
  }},
  "portfolio_match": {{
    "highlights": ["作品与岗位相关的亮点"],
    "gaps_or_risks": ["作品可能被质疑处"],
    "follow_up_angles": ["可追问但须服务于验证 JD 能力的角度"]
  }},
  "interview_focus": {{
    "jd_must_verify": ["面试中必须验证的 JD 能力/职责（优先于聊简历本身）"],
    "evidence_to_probe": ["宜从简历/作品切入、但落脚在 JD 胜任力的验证点"],
    "skepticism_points": ["面试官可能挑战的点（与 JD 风险相关）"]
  }},
  "summary": "一段话：先概括 JD 核心要求，再概括材料支撑与缺口（120字以内）"
}}

若作品集为空：portfolio_as_evidence、portfolio_match 中相关数组可为空列表，但不得省略 jd_decomposition。"""

# ===== 问题生成：JD 定考什么，简历/作品定从哪切入验证 =====
QUESTION_GENERATION_WITH_PORTFOLIO_PROMPT = """你是一位资深面试官，组织一场**以岗位 JD 为主轴**的模拟面试。

【输入说明】
- **JD**：考察的「考纲」——核心职责、必备能力、加分项、风险点。
- **匹配分析 JSON**：已包含 jd_decomposition、材料证据与缺口；生成问题时**优先使用其中的 JD 相关字段**。
- **简历摘要 / 作品集摘要**：仅用于**选题切入点、案例引用、验证缺口**，不得把面试变成「简历盘点会」。

【简历摘要】
{resume_summary}

【作品集摘要】
{portfolio_summary}

【岗位描述 JD】
{jd_text}

【匹配分析 JSON】
{match_analysis}

【出题原则（必须遵守）】
1) 先在脑中从 JD 提炼 **4～6 个最关键能力维度**（与 jd_decomposition 对齐），整卷问题**优先服务于验证这些维度**。
2) **问题必须优先对应 JD 的核心职责/必备能力/风险点**；简历、作品集只作为**证据来源、缺口来源或案例切入**，不得喧宾夺主。
3) 题目数量 **6～8 道**，比例建议：
   - **至少 4 道**：明确对应 JD 核心职责或必备能力（source 用 jd_core）；
   - **至少 1 道**：针对缺口、风险、能力迁移或补短板（source 用 jd_gap）；
   - **最多 2 道**：以简历或作品为切入点的深挖，但题干须写明**要验证的 JD 能力点**（source 用 resume_evidence 或 portfolio_evidence）；
   - **自我介绍**可 1 道，但全卷不得多数题都是「自我介绍 + 经历复述」（source 用 behavioral 或 jd_core，视题干是否锚定 JD）。
4) 每道题应能回答：**「这道题在验证候选人是否胜任 JD 的哪一条要求？」**——hint 里请简短写出对应的 JD 能力点或职责点。
5) 不要生成与 JD 明显无关的通用面试题；不要退化成与岗位无关的题库。

【source 字段取值（每题必填，便于调试）】
- jd_core：直接对应 JD 核心职责/必备能力
- jd_gap：缺口、风险、迁移、补短板
- resume_evidence：以简历经历为切入，验证 JD 能力
- portfolio_evidence：以作品为切入，验证 JD 能力
- behavioral：行为/情景类，但仍应能关联到 JD 中的软性能力或协作要求

直接输出 JSON 数组，不要其他说明：
[
  {{"id": 1, "type": "题型简述", "question": "题干", "hint": "对应 JD 能力点 + 追问方向", "source": "jd_core"}},
  {{"id": 2, "type": "...", "question": "...", "hint": "...", "source": "resume_evidence"}}
]"""

# ===== 追问：对齐主问题背后的 JD 能力，再要证据 =====
FOLLOW_UP_PROMPT = """你正在扮演真实面试官。追问的目标是：**判断候选人是否满足当前主问题所对应的 JD 能力/职责要求**，而不是单纯闲聊简历细节。

【候选人背景锚点（岗位与材料摘要，用于对齐 JD，勿复述全文）】
{candidate_background}

【当前主问题】
{question}

【考察/命题提示（含本题应对应的 JD 能力点）】
{hint}

【候选人本轮回答】
{user_answer}

【仅前序 1 题摘要（避免重复问法；无则忽略）】
{recent_history}

【上一轮追问文本（勿逐字重复；无则填「无」）】
{avoid_repeat}

硬性规则：
1) 先判断：本轮回答**是否给出了可验证的证据**（职责边界、结果、数据、协作、落地场景）以证明**胜任 JD 相关能力**；若明显不足，追问应索要**证据、结果、职责边界、能力迁移、岗位落地性**，避免泛泛的「举个例子」「结果如何」与 JD 无关。
2) 追问须结合【候选人背景锚点】与【当前主问题】；禁止与主问题题干重复。
3) 若回答已足够具体、可验证且能支撑 JD 相关能力，输出：NEXT_QUESTION。
4) 若需追问，只输出**一句**中文问句，无解释、无编号。
5) 勿重复【上一轮追问文本】。"""

# ===== 深度综合评价 + 逐题复盘 + 口语化 + 风险 =====
EVALUATION_DEEP_PROMPT = """你是资深面试官与表达教练。评价时必须**以岗位 JD 的胜任力要求为标尺**，结合候选人简历摘要、作品集摘要（如有）、目标 JD，以及下方完整模拟面试问答记录，输出**可执行的复盘**，避免空泛套话。

【简历摘要】
{resume_summary}

【作品集摘要】
{portfolio_summary}

【岗位描述 JD】
{jd_text}

【面试问答记录】
{interview_records}

请严格输出 JSON（不要输出其他说明）：
{{
  "overall_comment": "总评 150-250 字，必须引用候选人实际回答中的具体问题，并点出与 JD 要求的对齐或偏离",
  "scores": {{
    "jd_relevance": 0,
    "consistency_resume_portfolio": 0,
    "clarity": 0,
    "specificity": 0,
    "persuasion": 0,
    "professional_tone": 0,
    "job_match": 0,
    "tech_clarity": 0,
    "project_completeness": 0,
    "logic": 0,
    "communication": 0
  }},
  "answer_quality_notes": {{
    "vague_or_jargon": ["指出空泛/堆砌术语的具体说法（引用原话片段）"],
    "off_topic": ["跑题点"]
  }},
  "per_question_reviews": [
    {{
      "question_index": 1,
      "question": "题干",
      "interviewer_intent": "这题对应 JD 的哪项要求、考察什么",
      "strengths": "可取之处（结合其回答）",
      "issues": "主要问题（结合其回答）",
      "weak_phrases": ["表述不够好的原话片段"],
      "add_examples": "可补充的例子/数据/项目细节建议",
      "better_phrasing_spoken": "用**可直接说出口**的 2-4 句中文改写示例（口语、职业化，不要报告腔）"
    }}
  ],
  "oral_rewrites": [
    {{
      "dont_say": "不建议的说法（引用或概括原话）",
      "say_instead": "更自然、更像现场面试的说法（短句，可直接背）"
    }}
  ],
  "do_not_say": [
    "真实面试中建议避免的说法或承诺（具体到场景）"
  ],
  "risk_reminders": [
    "哪些说法易引发质疑；哪些点展开不好会暴露短板；建议主动补充 vs 点到为止"
  ],
  "improvement_suggestions": ["3-6 条可执行改进动作"],
  "optimized_expressions": [
    {{"original": "原表达", "suggested": "优化后口语版"}}
  ],
  "next_practice": ["下一轮刻意练习建议"]
}}

分数均为 1-10 的整数。per_question_reviews 需覆盖记录中出现的每一道主问题（与问答记录顺序一致）。"""

# 兼容旧代码：保留原名常量（若仍有引用）
MATCH_ANALYSIS_PROMPT = MATCH_ANALYSIS_WITH_PORTFOLIO_PROMPT
QUESTION_GENERATION_PROMPT = QUESTION_GENERATION_WITH_PORTFOLIO_PROMPT
EVALUATION_PROMPT = EVALUATION_DEEP_PROMPT
