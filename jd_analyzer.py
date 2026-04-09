# -*- coding: utf-8 -*-
"""
AI 模拟面试器 - 岗位描述(JD)分析模块
结合简历、可选作品集与 JD 做匹配分析并生成面试问题
"""

import json
from typing import Any, Dict, List, Optional

from llm_service import chat_json
from prompts import MATCH_ANALYSIS_WITH_PORTFOLIO_PROMPT, QUESTION_GENERATION_WITH_PORTFOLIO_PROMPT
from utils import truncate_text


def analyze_match(
    resume_text: str,
    jd_text: str,
    portfolio_text: Optional[str] = None,
) -> Dict[str, Any]:
    """
    分析简历、可选作品集与 JD 的匹配度。
    portfolio_text 为空时自动降级为仅简历+JD。
    """
    # 分析阶段保留充分信息，但避免超长上下文导致首轮变慢
    resume_text = truncate_text(resume_text or "", 5000)
    jd_text = truncate_text(jd_text or "", 2600)
    pt = (portfolio_text or "").strip()
    if not pt:
        pt = "（未提供作品集：本次分析仅基于简历与 JD。）"
    else:
        pt = truncate_text(pt, 3200)

    prompt = MATCH_ANALYSIS_WITH_PORTFOLIO_PROMPT.format(
        resume_text=resume_text,
        portfolio_text=pt,
        jd_text=jd_text,
    )

    messages = [{"role": "user", "content": prompt}]
    result = chat_json(messages, default={})

    if not result:
        return {
            "job_title_guess": "",
            "jd_decomposition": {
                "core_responsibilities": [],
                "must_have_capabilities": [],
                "bonus_points": [],
                "risk_or_skepticism_points": [],
            },
            "resume_as_evidence": {"supports_jd": [], "gaps_or_weak_evidence": []},
            "portfolio_as_evidence": {"supports_jd": [], "gaps_or_weak_evidence": []},
            "skill_match": {"matched_skills": [], "partially_matched": [], "missing_skills": []},
            "experience_match": {"strengths": [], "gaps": []},
            "portfolio_match": {"highlights": [], "gaps_or_risks": [], "follow_up_angles": []},
            "interview_focus": {
                "jd_must_verify": [],
                "evidence_to_probe": [],
                "skepticism_points": [],
            },
            "summary": "分析失败，请检查 API 配置",
        }
    return result


def generate_questions(
    resume_summary: str,
    jd_text: str,
    match_analysis: Dict,
    portfolio_summary: str = "",
) -> List[Dict]:
    """
    根据简历摘要、作品集摘要（可选）、JD 与匹配分析生成模拟面试问题。
    """
    resume_summary = truncate_text(resume_summary or "", 2000)
    jd_text = truncate_text(jd_text or "", 2000)
    ps = (portfolio_summary or "").strip()
    if not ps:
        ps = "（未提供作品集）"
    else:
        ps = truncate_text(ps, 2000)
    # 去掉缩进可显著减少 token，提升“生成题目”速度
    match_str = json.dumps(match_analysis, ensure_ascii=False, separators=(",", ":"))

    prompt = QUESTION_GENERATION_WITH_PORTFOLIO_PROMPT.format(
        resume_summary=resume_summary,
        portfolio_summary=ps,
        jd_text=jd_text,
        match_analysis=match_str,
    )

    messages = [{"role": "user", "content": prompt}]
    questions = chat_json(messages, default=[])

    if not isinstance(questions, list):
        questions = []

    _valid_source = frozenset({
        "jd_core", "jd_gap", "resume_evidence", "portfolio_evidence", "behavioral",
    })

    result = []
    for i, q in enumerate(questions):
        if isinstance(q, dict):
            src = (q.get("source") or "jd_core").strip()
            if src not in _valid_source:
                src = "jd_core"
            result.append({
                "id": q.get("id", i + 1),
                "type": q.get("type", "通用"),
                "question": q.get("question", str(q)),
                "hint": q.get("hint", ""),
                "source": src,
            })
        else:
            result.append({
                "id": i + 1,
                "type": "通用",
                "question": str(q),
                "hint": "",
                "source": "jd_core",
            })

    return result
