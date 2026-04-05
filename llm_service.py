# -*- coding: utf-8 -*-
"""
AI 模拟面试器 - LLM 服务模块
负责与 OpenAI 兼容 API 的交互
"""

import os
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI

from config_env import getenv_smart, getenv_smart_optional
from utils import safe_json_parse

load_dotenv()


def _default_timeout() -> float:
    return float(getenv_smart("OPENAI_TIMEOUT", "120"))


def get_client() -> Optional[OpenAI]:
    """获取 OpenAI 客户端"""
    api_key = getenv_smart("OPENAI_API_KEY", "")
    if not api_key:
        return None
    kwargs = {"api_key": api_key, "timeout": _default_timeout()}
    api_base = getenv_smart_optional("OPENAI_API_BASE")
    if api_base:
        kwargs["base_url"] = api_base
    return OpenAI(**kwargs)


def _model() -> str:
    return getenv_smart("LLM_MODEL", "gpt-4o-mini")


def chat_completion(
    messages: list,
    temperature: float = 0.7,
    max_tokens: int = 2000,
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
        # 超时由客户端 OpenAI(timeout=...) 控制；部分网关仍可能抛 Request timed out，可调大 OPENAI_TIMEOUT
        resp = client.chat.completions.create(
            model=_model(),
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content
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
