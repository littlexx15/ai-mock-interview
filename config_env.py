# -*- coding: utf-8 -*-
"""
环境变量与 Streamlit Secrets 统一读取。

本地开发：`.env` + python-dotenv（在 llm_service 等处 load_dotenv）。
Streamlit Community Cloud / 其他平台：在控制台配置 Secrets 或环境变量，
键名与 .env 一致（如 OPENAI_API_KEY），本模块会优先 os.environ，再尝试 st.secrets。
"""

import os
from typing import Optional


def getenv_smart(key: str, default: str = "") -> str:
    """优先环境变量，其次 Streamlit secrets。"""
    v = os.getenv(key)
    if v is not None and str(v).strip() != "":
        return str(v).strip()
    try:
        import streamlit as st

        if hasattr(st, "secrets") and key in st.secrets:
            s = str(st.secrets[key]).strip()
            if s:
                return s
    except Exception:
        pass
    return default


def getenv_smart_optional(key: str) -> Optional[str]:
    """可选字符串（空视为未设置）。"""
    v = os.getenv(key)
    if v is not None and str(v).strip() != "":
        return str(v).strip()
    try:
        import streamlit as st

        if hasattr(st, "secrets") and key in st.secrets:
            s = str(st.secrets[key]).strip()
            return s if s else None
    except Exception:
        pass
    return None
