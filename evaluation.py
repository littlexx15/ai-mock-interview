# -*- coding: utf-8 -*-
"""
AI 模拟面试器 - 评估模块
深度复盘：维度评分、逐题复盘、口语化改写、风险提醒
"""

from typing import Any, Dict, List

from llm_service import chat_json
from prompts import EVALUATION_DEEP_PROMPT
from utils import format_interview_record, truncate_text


def evaluate_interview(
    resume_summary: str,
    jd_text: str,
    records: List[Dict],
    portfolio_summary: str = "",
) -> Dict[str, Any]:
    """
    对完整面试进行综合评估（含作品集上下文，可选）。
    :param records: [{"question", "answer", "follow_up"?, "follow_up_answer"?}]
    """
    records_str = format_interview_record(records)
    resume_summary = truncate_text(resume_summary or "", 2000)
    jd_text = truncate_text(jd_text or "", 2000)
    ps = (portfolio_summary or "").strip()
    if not ps:
        ps = "（未提供作品集）"
    else:
        ps = truncate_text(ps, 2000)

    prompt = EVALUATION_DEEP_PROMPT.format(
        resume_summary=resume_summary,
        portfolio_summary=ps,
        jd_text=jd_text,
        interview_records=records_str,
    )

    messages = [{"role": "user", "content": prompt}]
    nrec = len(records or [])
    print("[eval] start records=%s resume_chars=%s jd_chars=%s" % (nrec, len(resume_summary or ""), len(jd_text or "")))

    # 深度复盘 JSON 很大，默认 2000 token 易截断导致解析失败 → 页面“像没生成”
    result = chat_json(
        messages,
        default=None,
        max_tokens=12000,
        temperature=0.35,
    )

    if result is None:
        print("[eval] chat_json returned None (API 失败或 JSON 解析失败)")
        return _default_eval()

    if not isinstance(result, dict):
        print("[eval] unexpected result type: %s" % type(result))
        return _default_eval()

    print("[eval] ok keys=%s" % list(result.keys())[:12])
    return _normalize_eval_result(result)


def _normalize_eval_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """补齐字段，兼容旧版 scores 键。"""
    default_scores = {
        "jd_relevance": 6,
        "consistency_resume_portfolio": 6,
        "clarity": 6,
        "specificity": 6,
        "persuasion": 6,
        "professional_tone": 6,
        "job_match": 6,
        "tech_clarity": 6,
        "project_completeness": 6,
        "logic": 6,
        "communication": 6,
    }
    scores = result.get("scores", {}) or {}
    for k, v in default_scores.items():
        if k not in scores:
            scores[k] = v
    result["scores"] = scores

    result.setdefault("overall_comment", "评估完成")
    result.setdefault("answer_quality_notes", {"vague_or_jargon": [], "off_topic": []})
    result.setdefault("per_question_reviews", [])
    result.setdefault("oral_rewrites", [])
    result.setdefault("do_not_say", [])
    result.setdefault("risk_reminders", [])
    result.setdefault("improvement_suggestions", [])
    result.setdefault("optimized_expressions", [])
    result.setdefault("next_practice", [])

    return result


def _default_eval() -> Dict:
    """API 失败时的默认评估"""
    return {
        "overall_comment": "评估服务暂时不可用，请检查 API 配置后重试。",
        "scores": {
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
            "communication": 0,
        },
        "answer_quality_notes": {"vague_or_jargon": [], "off_topic": []},
        "per_question_reviews": [],
        "oral_rewrites": [],
        "do_not_say": [],
        "risk_reminders": [],
        "improvement_suggestions": ["请确认 OPENAI_API_KEY 已正确配置"],
        "optimized_expressions": [],
        "next_practice": [],
    }
