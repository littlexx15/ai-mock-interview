# -*- coding: utf-8 -*-
"""
环境变量与 Streamlit Secrets 统一读取。

本地开发：`.env` + python-dotenv（在 llm_service 等处 load_dotenv）。
Streamlit Community Cloud / 其他平台：在控制台配置 Secrets 或环境变量，
键名与 .env 一致（如 OPENAI_API_KEY），本模块会优先 os.environ，再尝试 st.secrets。
"""

import os
from typing import Dict, List, Optional


def _secret_lookup(key: str) -> Optional[str]:
    """在 Streamlit secrets 中查找键，兼容平铺与分组结构。"""
    try:
        import streamlit as st

        if not hasattr(st, "secrets"):
            return None
        secrets = st.secrets

        # 1) 平铺键：OPENAI_API_KEY
        if key in secrets:
            s = str(secrets[key]).strip()
            return s if s else None

        # 2) 分组键：openai.api_key / speech.api_base
        lower_key = key.lower()
        for group_name in ("openai", "speech", "llm"):
            grp = secrets.get(group_name)
            if isinstance(grp, dict):
                for k, v in grp.items():
                    if f"{group_name}_{str(k).lower()}" == lower_key:
                        s = str(v).strip()
                        return s if s else None
    except Exception:
        return None
    return None


def getenv_smart(key: str, default: str = "") -> str:
    """优先环境变量，其次 Streamlit secrets。"""
    v = os.getenv(key)
    if v is not None and str(v).strip() != "":
        return str(v).strip()
    s = _secret_lookup(key)
    if s:
        return s
    return default


def getenv_smart_optional(key: str) -> Optional[str]:
    """可选字符串（空视为未设置）。"""
    v = os.getenv(key)
    if v is not None and str(v).strip() != "":
        return str(v).strip()
    return _secret_lookup(key)


def get_text_llm_config() -> Dict[str, str]:
    """统一读取文本 LLM 配置。"""
    return {
        "api_key": getenv_smart("OPENAI_API_KEY", ""),
        "api_base": getenv_smart("OPENAI_API_BASE", ""),
        "model": getenv_smart("LLM_MODEL", ""),
        "timeout": getenv_smart("OPENAI_TIMEOUT", "180"),
    }


def get_speech_config() -> Dict[str, str]:
    """统一读取语音 STT/TTS 配置。"""
    return {
        "api_key": getenv_smart("SPEECH_API_KEY", ""),
        "stt_api_base": getenv_smart("STT_API_BASE", ""),
        "stt_model": getenv_smart("STT_MODEL", ""),
        "tts_api_base": getenv_smart("TTS_API_BASE", ""),
        "tts_model": getenv_smart("TTS_MODEL", ""),
        "tts_voice": getenv_smart("TTS_VOICE", "alloy"),
    }


def missing_text_llm_keys() -> List[str]:
    cfg = get_text_llm_config()
    required = {
        "OPENAI_API_KEY": cfg["api_key"],
        "LLM_MODEL": cfg["model"],
    }
    return [k for k, v in required.items() if not str(v).strip()]


def missing_speech_keys() -> List[str]:
    cfg = get_speech_config()
    required = {
        "SPEECH_API_KEY": cfg["api_key"],
        "STT_API_BASE": cfg["stt_api_base"],
        "STT_MODEL": cfg["stt_model"],
        "TTS_API_BASE": cfg["tts_api_base"],
        "TTS_MODEL": cfg["tts_model"],
    }
    return [k for k, v in required.items() if not str(v).strip()]


def is_text_llm_ready() -> bool:
    return len(missing_text_llm_keys()) == 0


def is_speech_ready() -> bool:
    return len(missing_speech_keys()) == 0


def get_runtime_diag() -> Dict[str, str]:
    """
    返回可安全展示的配置诊断信息（不含明文 key）。
    """
    text = get_text_llm_config()
    speech = get_speech_config()
    return {
        "text_key_exists": "yes" if bool((text.get("api_key") or "").strip()) else "no",
        "text_base_url": (text.get("api_base") or "").strip(),
        "text_model": (text.get("model") or "").strip(),
        "text_timeout": (text.get("timeout") or "").strip(),
        "speech_key_exists": "yes" if bool((speech.get("api_key") or "").strip()) else "no",
        "speech_stt_base_url": (speech.get("stt_api_base") or "").strip(),
        "stt_model": (speech.get("stt_model") or "").strip(),
        "speech_tts_base_url": (speech.get("tts_api_base") or "").strip(),
        "tts_model": (speech.get("tts_model") or "").strip(),
        "tts_voice": (speech.get("tts_voice") or "").strip(),
    }
