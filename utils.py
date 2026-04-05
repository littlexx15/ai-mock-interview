# -*- coding: utf-8 -*-
"""
AI 模拟面试器 - 通用工具函数
"""

import json
import re
from typing import Any, Dict, List, Optional

# 深度复盘 scores 字典的英文 key → 中文展示名（JSON 仍用英文键）
SCORE_DIMENSION_LABELS_ZH: Dict[str, str] = {
    "jd_relevance": "与 JD 的相关性",
    "consistency_resume_portfolio": "与简历/作品集的一致性",
    "clarity": "表达清晰度",
    "specificity": "回答具体程度",
    "persuasion": "说服力",
    "professional_tone": "职业化 / 岗位语感",
    "job_match": "岗位匹配度",
    "tech_clarity": "技术表达清晰度",
    "project_completeness": "项目表达完整度",
    "logic": "逻辑性",
    "communication": "沟通表现",
}


def score_dimension_label_zh(key: str) -> str:
    """维度分数字段名转中文，未知 key 原样返回。"""
    return SCORE_DIMENSION_LABELS_ZH.get(key, key)


def safe_json_parse(text: str) -> Any:
    """
    安全解析 JSON，支持从文本中提取 JSON 块
    """
    text = text.strip()
    # 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 尝试提取 {} 或 [] 包裹的内容
    for pattern in [r'\{[\s\S]*\}', r'\[[\s\S]*\]']:
        match = re.search(pattern, text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                continue

    return None


def truncate_text(text: str, max_len: int = 8000) -> str:
    """截断文本，避免超出模型上下文"""
    if len(text) <= max_len:
        return text
    return text[:max_len] + "\n...[已截断]"


def extract_keywords(text: str, top_n: int = 20) -> List[str]:
    """
    简单提取文本中的关键词（技术词汇等）
    用于简历摘要和快速匹配
    """
    # 常见技术/技能关键词（可扩展）
    common_tech = [
        "Python", "Java", "JavaScript", "React", "Vue", "MySQL", "Redis",
        "Docker", "Kubernetes", "机器学习", "深度学习", "NLP", "数据分析",
        "项目管理", "团队协作", "沟通", "领导力"
    ]
    found = []
    text_lower = text.lower()
    for kw in common_tech:
        if kw.lower() in text_lower:
            found.append(kw)
    return found[:top_n]


def format_interview_record(qa_list: List[Dict[str, str]]) -> str:
    """将问答记录格式化为字符串，便于 LLM 理解"""
    lines = []
    for i, qa in enumerate(qa_list, 1):
        lines.append(f"Q{i}: {qa.get('question', '')}")
        lines.append(f"A{i}: {qa.get('answer', '')}")
        if qa.get('follow_up'):
            lines.append(f"追问: {qa['follow_up']}")
            lines.append(f"答: {qa.get('follow_up_answer', '')}")
    return "\n".join(lines)
