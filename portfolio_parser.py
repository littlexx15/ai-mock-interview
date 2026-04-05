# -*- coding: utf-8 -*-
"""
作品集解析模块（MVP）
支持 PDF / DOCX / TXT 文本提取；图片 OCR 预留接口。
实现上与简历解析共用同一套文档字节解析逻辑，便于维护。
"""

from typing import Dict, Optional

from resume_parser import parse_resume


def parse_portfolio(
    file_path: Optional[str] = None,
    file_bytes: Optional[bytes] = None,
    filename: Optional[str] = None,
) -> Dict:
    """
    解析作品集文件，返回与简历解析一致的结构：
    raw_text, summary, keywords, projects, error
    """
    return parse_resume(file_path=file_path, file_bytes=file_bytes, filename=filename)


def parse_portfolio_image(
    file_path: Optional[str] = None,
    file_bytes: Optional[bytes] = None,
) -> Dict:
    """
    图片类作品集 OCR（预留）
    后续可接入 PaddleOCR / Vision API 等，与简历图片 OCR 可复用同一实现。
    """
    return {
        "raw_text": "",
        "summary": "",
        "keywords": [],
        "projects": [],
        "error": "图片作品集 OCR 尚未实现，请使用 PDF/DOCX/TXT",
    }
