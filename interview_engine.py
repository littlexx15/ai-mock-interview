# -*- coding: utf-8 -*-
"""
AI 模拟面试器 - 面试引擎
管理面试流程、提问、追问
"""

import os
from typing import Dict, List, Optional

from llm_service import chat_completion
from prompts import FOLLOW_UP_PROMPT

# LLM 超时/失败时使用：与「主问题题干」字面不同，明确是追问语气，避免页面像「同一题问两遍」
FOLLOW_UP_FALLBACK = (
    "结合你刚才的回答，请任选其中一段经历展开：你个人具体负责哪部分、关键决策是什么、如何衡量结果？"
)


def _format_prior_records_light(records: Optional[List[Dict]], max_items: int = 1) -> str:
    """轻量化前序上下文：只保留最近 1 道题的一行摘要，减少追问请求的 token 与延迟。"""
    if not records:
        return "（此前尚未完成其他题目）"
    lines = []
    for rec in records[-max_items:]:
        q = (rec.get("question") or "")[:100]
        a = (rec.get("answer") or "")[:180]
        lines.append(f"前序：{q}… | 答：{a}…")
        if rec.get("follow_up"):
            lines.append(f"前序追问：{(rec.get('follow_up') or '')[:80]}…")
    return "\n".join(lines)


def _follow_up_model() -> Optional[str]:
    """
    追问模型可单独配置（双模型策略）。
    未配置 FOLLOW_UP_MODEL 时沿用主模型。
    """
    m = (os.getenv("FOLLOW_UP_MODEL") or "").strip()
    return m or None


def get_follow_up(
    question: str,
    user_answer: str,
    hint: str,
    candidate_background: str = "",
    prior_records: Optional[List[Dict]] = None,
    last_follow_up_question: str = "",
) -> Optional[str]:
    """
    根据用户回答生成追问（轻量上下文：岗位锚点 + 本题 + 最近回答 + 极简前序）。
    :return: 追问内容，若无需追问返回 "NEXT_QUESTION"
    """
    recent_history = _format_prior_records_light(prior_records, max_items=1)
    bg = (candidate_background or "").strip()[:1200]
    if not bg:
        bg = "（未提供候选人背景摘要）"
    avoid = (last_follow_up_question or "").strip()[:500]
    prompt = FOLLOW_UP_PROMPT.format(
        question=question,
        user_answer=user_answer,
        hint=hint or "无",
        candidate_background=bg,
        recent_history=recent_history,
        avoid_repeat=avoid or "（无）",
    )
    # 调试：定位追问是否用到最新回答
    print(
        "[follow_up] q_len=%s ans_len=%s hist_chars=%s preview_ans=%r"
        % (
            len(question or ""),
            len(user_answer or ""),
            len(recent_history),
            (user_answer or "")[:120],
        )
    )
    messages = [{"role": "user", "content": prompt}]
    resp = chat_completion(messages, temperature=0.82, max_tokens=220, model=_follow_up_model())
    if not resp:
        print("[follow_up] LLM 返回空（常见：超时），将重试一次")
        resp = chat_completion(messages, temperature=0.86, max_tokens=220, model=_follow_up_model())
    if not resp:
        # 不再返回 NEXT_QUESTION：否则用户看不到任何「追问」，页面上会像只答了主问题就跳题
        print("[follow_up] 仍失败，使用兜底追问句（与主问题题干不同）")
        return FOLLOW_UP_FALLBACK
    text = resp.strip()
    if not text:
        return FOLLOW_UP_FALLBACK
    first_line = text.strip().splitlines()[0].strip().upper()
    if first_line == "NEXT_QUESTION":
        return "NEXT_QUESTION"
    # 避免与上一轮追问字面完全相同（模板化重复）
    if avoid and text == avoid:
        print("[follow_up] repeat detected, retry once")
        messages_retry = [
            {
                "role": "user",
                "content": prompt
                + "\n\n【重要】你刚才的追问与上一轮完全相同，请换一个完全不同的切入角度，仍只输出一行追问或 NEXT_QUESTION。",
            }
        ]
        resp2 = chat_completion(messages_retry, temperature=0.9, max_tokens=220, model=_follow_up_model())
        text = (resp2 or text).strip() or FOLLOW_UP_FALLBACK
    return text


def build_interview_state(
    questions: List[Dict],
    resume_summary: str,
    jd_text: str,
    portfolio_summary: str = "",
    job_title: str = "",
    candidate_background_snippet: str = "",
) -> Dict:
    """
    构建面试状态对象，供 Streamlit session_state 使用
    """
    return {
        "questions": questions,
        "resume_summary": resume_summary,
        "jd_text": jd_text,
        "portfolio_summary": portfolio_summary or "",
        "job_title": job_title or "",
        "candidate_background_snippet": (candidate_background_snippet or "")[:2000],
        "current_index": 0,
        "records": [],  # [{"question", "answer", "follow_up", "follow_up_answer"}]
        "phase": "interviewing",  # interviewing | evaluating
        "follow_up_asked": False,
        "follow_up_answer": "",
        "_prev_follow_up_text": "",
    }


def get_current_question(state: Dict) -> Optional[Dict]:
    """获取当前应提问的问题"""
    idx = state.get("current_index", 0)
    qs = state.get("questions", [])
    if 0 <= idx < len(qs):
        return qs[idx]
    return None


def advance_after_follow_up(state: Dict) -> None:
    """完成追问后进入下一题"""
    state["current_index"] = state.get("current_index", 0) + 1
    state["follow_up_asked"] = False
    state["follow_up_answer"] = ""


def add_record(
    state: Dict,
    question: str,
    answer: str,
    follow_up: Optional[str] = None,
    follow_up_answer: Optional[str] = None
) -> None:
    """添加一条问答记录"""
    rec = {"question": question, "answer": answer}
    if follow_up:
        rec["follow_up"] = follow_up
        rec["follow_up_answer"] = follow_up_answer or ""
    state["records"].append(rec)


def interview_records_for_eval(state: Dict) -> List[Dict]:
    """获取完整问答记录，供评估使用"""
    return state.get("records", [])
