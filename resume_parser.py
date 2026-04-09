# -*- coding: utf-8 -*-
"""
AI 模拟面试器 - 简历解析模块
支持 PDF、DOCX、TXT，预留图片 OCR 接口
"""

import io
from pathlib import Path
from typing import Dict, List, Optional

# PDF
try:
    from PyPDF2 import PdfReader
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

# DOCX
try:
    from docx import Document
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

from utils import extract_keywords


# 支持的文件类型
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}  # 预留


def parse_resume(file_path: Optional[str] = None, file_bytes: Optional[bytes] = None, filename: Optional[str] = None) -> Dict:
    """
    解析简历文件
    :param file_path: 文件路径（与 file_bytes 二选一）
    :param file_bytes: 文件字节（上传时用）
    :param filename: 文件名，用于判断类型
    :return: {"raw_text": str, "summary": str, "keywords": list, "projects": list, "error": str?}
    """
    result = {
        "raw_text": "",
        "summary": "",
        "keywords": [],
        "projects": [],
        "error": None
    }

    ext = ""
    if filename:
        ext = Path(filename).suffix.lower()
    elif file_path:
        ext = Path(file_path).suffix.lower()

    # 图片类型：预留接口
    if ext in IMAGE_EXTENSIONS:
        result["error"] = "图片简历 OCR 功能尚未实现，请使用 PDF/DOCX/TXT"
        return result

    if ext not in SUPPORTED_EXTENSIONS:
        result["error"] = f"不支持的文件格式: {ext}，请使用 PDF、DOCX 或 TXT"
        return result

    raw_text = ""

    try:
        if file_bytes:
            raw_text = _parse_from_bytes(file_bytes, ext)
        elif file_path:
            with open(file_path, "rb") as f:
                raw_text = _parse_from_bytes(f.read(), ext)
    except Exception as e:
        result["error"] = f"解析失败: {str(e)}"
        return result

    if not (raw_text or "").strip():
        result["error"] = "未能从文件中提取到文本内容（可能是扫描版/图片型 PDF、加密文档或空文件）"
        return result

    result["raw_text"] = raw_text
    result["keywords"] = extract_keywords(raw_text)
    result["summary"] = _make_summary(raw_text)
    result["projects"] = _extract_projects(raw_text)
    return result


def _parse_from_bytes(data: bytes, ext: str) -> str:
    """从字节解析文本"""
    if ext == ".pdf":
        if not HAS_PDF:
            raise ImportError("请安装 PyPDF2: pip install PyPDF2")
        reader = PdfReader(io.BytesIO(data))
        return "\n".join(p.extract_text() or "" for p in reader.pages)
    elif ext == ".docx":
        if not HAS_DOCX:
            raise ImportError("请安装 python-docx: pip install python-docx")
        doc = Document(io.BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs)
    elif ext == ".txt":
        return data.decode("utf-8", errors="ignore")
    return ""


def _make_summary(text: str, max_len: int = 1500) -> str:
    """生成简历摘要"""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    summary = "\n".join(lines[:80])
    if len(summary) > max_len:
        summary = summary[:max_len] + "..."
    return summary


def _extract_projects(text: str) -> List[str]:
    """简单提取项目段落（基于关键词）"""
    projects = []
    blocks = text.split("\n\n")
    for block in blocks:
        block_lower = block.lower()
        if any(kw in block_lower for kw in ["项目", "project", "经验", "experience", "工作"]):
            if len(block) > 30:
                projects.append(block[:500])
    return projects[:5]


# ===== 图片 OCR 预留接口 =====
def parse_resume_image(file_path: Optional[str] = None, file_bytes: Optional[bytes] = None) -> Dict:
    """
    图片简历 OCR 解析（第二阶段实现）
    预留接口
    """
    return {
        "raw_text": "",
        "summary": "",
        "keywords": [],
        "projects": [],
        "error": "图片 OCR 功能尚未实现"
    }
