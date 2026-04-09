# -*- coding: utf-8 -*-
"""
AI 模拟面试器 - LLM 服务模块
负责与 OpenAI 兼容 API 的交互（如 OpenAI、DeepSeek 等）。
"""

from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI

from config_env import getenv_smart, getenv_smart_optional
from utils import safe_json_parse

load_dotenv()


def _default_timeout() -> float:
    return float(getenv_smart("OPENAI_TIMEOUT", "120"))


def get_client() -> Optional[OpenAI]:
    """
    文本对话（chat）客户端。
    配置：OPENAI_API_KEY、OPENAI_API_BASE（如 https://api.deepseek.com/v1）、LLM_MODEL、OPENAI_TIMEOUT。
    """
    api_key = getenv_smart("OPENAI_API_KEY", "")
    if not api_key:
        return None
    kwargs = {"api_key": api_key, "timeout": _default_timeout()}
    api_base = getenv_smart_optional("OPENAI_API_BASE")
    if api_base:
        kwargs["base_url"] = api_base.rstrip("/")
    return OpenAI(**kwargs)


def get_speech_client() -> Optional[OpenAI]:
    """
    语音 STT/TTS 客户端（需支持 OpenAI Audio 的网关）。

    DeepSeek 聊天域名不提供 whisper/tts：若 LLM 走 DeepSeek，请另设
    SPEECH_API_BASE（如 https://api.openai.com/v1）与 SPEECH_API_KEY（OpenAI 密钥），
    详见 .env.example。
    """
    key = getenv_smart_optional("SPEECH_API_KEY") or getenv_smart("OPENAI_API_KEY", "")
    if not key:
        return None
    kwargs = {"api_key": key, "timeout": _default_timeout()}
    base = getenv_smart_optional("SPEECH_API_BASE") or getenv_smart_optional("OPENAI_API_BASE")
    if base:
        kwargs["base_url"] = base.rstrip("/")
    return OpenAI(**kwargs)


def _model() -> str:
    return getenv_smart("LLM_MODEL", "deepseek-chat")


def chat_completion(
    messages: list,
    temperature: float = 0.7,
    max_tokens: int = 2000,
    model: Optional[str] = None,
) -> Optional[str]:
    """
    调用 LLM 完成对话
    :param messages: [{"role": "user/assistant/system", "content": "..."}]
    :return: 助手回复内容，失败返回 None
    """
    client = get_client()
    if not client:
        return None

    try:
        use_model = (model or "").strip() or _model()
        resp = client.chat.completions.create(
            model=use_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        msg = resp.choices[0].message
        content = getattr(msg, "content", None) if msg else None
        return (content or "").strip() or None
    except Exception as e:
        print(f"LLM 调用异常: {e}")
        return None


def chat_json(
    messages: list,
    default: any = None,
    max_tokens: int = 2000,
    temperature: float = 0.7,
) -> any:
    """
    调用 LLM 并尝试解析为 JSON
    """
    content = chat_completion(messages, temperature=temperature, max_tokens=max_tokens)
    if not content:
        return default
    parsed = safe_json_parse(content)
    if parsed is None:
        return default
    return parsed
