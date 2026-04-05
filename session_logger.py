# -*- coding: utf-8 -*-
"""
面试会话日志：统一结构、从 state 同步、导出 JSON / Markdown
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List

from utils import score_dimension_label_zh


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def new_interview_log(
    *,
    mode: str,
    job_title: str,
    resume_summary: str,
    portfolio_summary: str,
    jd_text: str,
    match_analysis: Any,
    questions: List[Dict],
) -> Dict[str, Any]:
    """创建新会话日志骨架（分析完成后调用）。"""
    return {
        "meta": {
            "created_at": _now_iso(),
            "mode": mode,
            "job_title": job_title or "未识别岗位名",
            "questions_count": len(questions),
        },
        "inputs": {
            "resume_summary": resume_summary or "",
            "portfolio_summary": portfolio_summary or "",
            "jd_text": jd_text or "",
            "jd_excerpt": (jd_text or "")[:1200],
        },
        "analysis": match_analysis if isinstance(match_analysis, dict) else {},
        "qa_log": [],
        "final_report": None,
    }


def sync_qa_log_from_state(interview_log: Dict[str, Any], state: Dict[str, Any], mode: str) -> None:
    """
    根据 interview_engine 的 records 重建 qa_log（导出前或与界面同步）。
    mode: 当前交互模式，写入每条回答的 answer_mode。
    """
    records: List[Dict] = state.get("records") or []
    qa: List[Dict[str, Any]] = []
    for i, rec in enumerate(records, start=1):
        entry: Dict[str, Any] = {
            "question_id": i,
            "question": rec.get("question", ""),
            "answer": rec.get("answer", ""),
            "answer_mode": mode,
            "follow_ups": [],
        }
        if rec.get("follow_up"):
            entry["follow_ups"].append(
                {
                    "question": rec.get("follow_up", ""),
                    "answer": rec.get("follow_up_answer", ""),
                    "mode": mode,
                }
            )
        qa.append(entry)
    interview_log["qa_log"] = qa


def attach_final_report(interview_log: Dict[str, Any], eval_result: Dict[str, Any]) -> None:
    """挂载最终评价结果。"""
    interview_log["final_report"] = eval_result
    interview_log["meta"]["completed_at"] = _now_iso()


def log_to_json(interview_log: Dict[str, Any]) -> str:
    return json.dumps(interview_log, ensure_ascii=False, indent=2)


def log_to_markdown(interview_log: Dict[str, Any]) -> str:
    """生成可阅读的 Markdown 日志。"""
    lines: List[str] = []
    meta = interview_log.get("meta") or {}
    lines.append("# 模拟面试完整日志\n")
    lines.append(f"- 开始时间: {meta.get('created_at', '')}")
    lines.append(f"- 完成时间: {meta.get('completed_at', '')}")
    lines.append(f"- 模式: {meta.get('mode', '')}")
    lines.append(f"- 岗位名称: {meta.get('job_title', '')}")
    lines.append(f"- 题目数量: {meta.get('questions_count', '')}\n")

    inp = interview_log.get("inputs") or {}
    lines.append("## 输入材料摘要\n")
    lines.append("### 简历摘要\n")
    lines.append((inp.get("resume_summary") or "（无）") + "\n")
    lines.append("### 作品集摘要\n")
    lines.append((inp.get("portfolio_summary") or "（未上传）") + "\n")
    lines.append("### JD 摘录\n")
    lines.append((inp.get("jd_excerpt") or inp.get("jd_text") or "（无）")[:2000] + "\n")

    lines.append("## 匹配分析\n")
    lines.append("```json\n")
    try:
        lines.append(json.dumps(interview_log.get("analysis") or {}, ensure_ascii=False, indent=2))
    except Exception:
        lines.append(str(interview_log.get("analysis")))
    lines.append("\n```\n")

    lines.append("## 问答记录\n")
    for item in interview_log.get("qa_log") or []:
        lines.append(f"### 第 {item.get('question_id')} 题\n")
        lines.append(f"- **问题**: {item.get('question', '')}\n")
        lines.append(f"- **回答**（{item.get('answer_mode', '')}）: {item.get('answer', '')}\n")
        for j, fu in enumerate(item.get("follow_ups") or [], start=1):
            lines.append(f"- **追问{j}**: {fu.get('question', '')}\n")
            lines.append(f"- **追问回答**（{fu.get('mode', '')}）: {fu.get('answer', '')}\n")

    fr = interview_log.get("final_report")
    lines.append("## 最终综合评价\n")
    if not fr:
        lines.append("（尚未生成）\n")
    else:
        lines.append(fr.get("overall_comment", "") + "\n")
        scores = fr.get("scores") or {}
        if scores:
            lines.append("\n### 维度评分\n")
            for k, v in scores.items():
                lines.append(f"- {score_dimension_label_zh(k)}: {v}\n")
        sugg = fr.get("improvement_suggestions") or []
        if sugg:
            lines.append("\n### 改进建议\n")
            for s in sugg:
                lines.append(f"- {s}\n")
        pqr = fr.get("per_question_reviews") or []
        if pqr:
            lines.append("\n### 逐题复盘\n")
            for pq in pqr:
                lines.append(f"- **题号** {pq.get('question_index', '')}: {pq.get('question', '')}\n")
                lines.append(f"  - 考察意图: {pq.get('interviewer_intent', '')}\n")
                lines.append(f"  - 亮点: {pq.get('strengths', '')}\n")
                lines.append(f"  - 问题: {pq.get('issues', '')}\n")
        risks = fr.get("risk_reminders") or []
        if risks:
            lines.append("\n### 风险提醒\n")
            for r in risks:
                lines.append(f"- {r}\n")
    return "\n".join(lines)
