# -*- coding: utf-8 -*-
"""
AI 模拟面试器 - 语音服务模块
实现：语音输入（STT）与语音播报（TTS）
"""

import base64
from typing import Any, Dict, List, Optional, Tuple

from openai import OpenAI

from config_env import get_speech_config, get_text_llm_config, is_speech_ready


def _log_exception(prefix: str, e: Exception) -> None:
    print(f"{prefix}: type={type(e).__name__} str={str(e)} repr={repr(e)}")


def _build_client(api_base: str) -> Optional[OpenAI]:
    """按指定 base_url 构建语音客户端。"""
    cfg = get_speech_config()
    api_key = (cfg.get("api_key") or "").strip()
    if not api_key:
        return None
    raw_timeout = (get_text_llm_config().get("timeout") or "").strip()
    try:
        timeout = float(raw_timeout or "180")
    except Exception:
        timeout = 180.0
    kwargs = {"api_key": api_key, "timeout": timeout}
    base = (api_base or "").strip()
    if not base:
        return None
    kwargs["base_url"] = base.rstrip("/")
    return OpenAI(**kwargs)


def get_stt_client() -> Optional[OpenAI]:
    cfg = get_speech_config()
    return _build_client(cfg.get("stt_api_base") or "")


def get_tts_client() -> Optional[OpenAI]:
    cfg = get_speech_config()
    return _build_client(cfg.get("tts_api_base") or "")


def _guess_filename_and_mime(audio_format: str) -> Tuple[str, str]:
    """
    根据格式猜测文件名与 mime

    新增说明：OpenAI 的转写接口需要一个“像文件一样”的对象（带 filename 更稳）。
    """
    fmt = (audio_format or "").lower().strip().lstrip(".")
    if fmt in {"mp3", "mpeg"}:
        return "answer.mp3", "audio/mpeg"
    if fmt in {"wav", "wave"}:
        return "answer.wav", "audio/wav"
    if fmt in {"m4a"}:
        return "answer.m4a", "audio/mp4"
    if fmt in {"ogg", "oga"}:
        return "answer.ogg", "audio/ogg"
    if fmt in {"webm"}:
        return "answer.webm", "audio/webm"
    # 兜底：按 wav 处理（很多浏览器录音会给 wav）
    return "answer.wav", "audio/wav"


def _transcription_to_dict(resp: Any) -> Dict[str, Any]:
    """将 SDK 返回对象尽量转为 dict，便于统一解析。"""
    if resp is None:
        return {}
    if isinstance(resp, dict):
        return resp
    if hasattr(resp, "model_dump"):
        try:
            return resp.model_dump()  # type: ignore[no-any-return]
        except Exception:
            pass
    return {}


def speech_to_text(audio_data: bytes, audio_format: str = "wav") -> Optional[str]:
    """
    语音转文字（STT）

    - 使用 OpenAI 兼容 API 的音频转写能力（模型由 STT_MODEL 提供）。
    - 说明：返回纯文本，供上层继续走原有“文本面试”逻辑。

    :param audio_data: 音频字节
    :param audio_format: 格式 wav/mp3/webm 等（尽量传真实格式）
    :return: 识别出的文字（失败返回 None）
    """
    text, _segments = speech_to_text_verbose(audio_data, audio_format=audio_format)
    return text


def speech_to_text_verbose(
    audio_data: bytes,
    audio_format: str = "wav",
) -> Tuple[Optional[str], List[Dict[str, Any]]]:
    """
    语音转文字（STT，verbose）

    - 优先使用 verbose_json，解析 segments，用于“分段字幕 / 准实时累加展示”。
    - 若兼容 API 不支持 verbose_json，则自动回退为普通转写（segments 为空列表）。

    :return: (全文, segments)；segment 形如 {"text", "start", "end"}
    """
    client = get_stt_client()
    if not client:
        return None, []

    cfg = get_speech_config()
    stt_model = (cfg.get("stt_model") or "").strip()
    stt_api_base = (cfg.get("stt_api_base") or "").strip()
    if not stt_model:
        return None, []

    _filename, mime = _guess_filename_and_mime(audio_format)
    print(
        "[stt] request model=%s base_url=%s audio_bytes=%s mime_type=%s"
        % (stt_model, stt_api_base, len(audio_data or b""), mime)
    )

    try:
        b64 = base64.b64encode(audio_data or b"").decode("ascii")
        data_url = f"data:{mime};base64,{b64}"

        completion = client.chat.completions.create(
            model=stt_model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": data_url,
                            },
                        }
                    ],
                }
            ],
            extra_body={
                "asr_options": {
                    "enable_itn": False,
                }
            },
        )
        print("[stt] raw completion object:", completion)
        print("[stt] repr(completion):", repr(completion))

        msg = completion.choices[0].message if completion and completion.choices else None
        content = getattr(msg, "content", None) if msg else None
        if isinstance(content, str):
            text = content.strip()
            return (text or None), []
        if isinstance(content, list):
            texts: List[str] = []
            for item in content:
                if isinstance(item, dict):
                    t = (item.get("text") or "").strip()
                    if t:
                        texts.append(t)
                else:
                    t = (getattr(item, "text", "") or "").strip()
                    if t:
                        texts.append(t)
            merged = "\n".join(texts).strip()
            return (merged or None), []
        return None, []
    except Exception as e:
        _log_exception("STT 转写异常", e)
        return None, []


def text_to_speech(text: str, output_path: Optional[str] = None) -> Optional[bytes]:
    """
    文字转语音（TTS）

    - 使用 OpenAI 兼容 API 的语音合成能力。
    - 返回：默认输出 mp3 字节，便于 Streamlit 直接 `st.audio()` 播放。

    :param text: 要朗读的文字
    :param output_path: 保存路径，可选（用于离线留存/调试）
    :return: 音频字节（失败返回 None）
    """
    client = get_tts_client()
    if not client:
        return None

    cfg = get_speech_config()
    tts_model = (cfg.get("tts_model") or "").strip()
    tts_voice = (cfg.get("tts_voice") or "").strip() or "alloy"
    tts_api_base = (cfg.get("tts_api_base") or "").strip()
    if not tts_model:
        return None

    print("[tts] request model=%s base_url=%s voice=%s" % (tts_model, tts_api_base, tts_voice))
    try:
        resp = client.audio.speech.create(
            model=tts_model,
            voice=tts_voice,
            input=text,
            format="mp3",
        )
        audio_bytes = resp.read() if hasattr(resp, "read") else bytes(resp)
        if output_path:
            with open(output_path, "wb") as f:
                f.write(audio_bytes)
        return audio_bytes
    except Exception as e:
        _log_exception("TTS 合成首轮失败", e)
        # 部分兼容网关使用 response_format 参数名
        try:
            resp = client.audio.speech.create(
                model=tts_model,
                voice=tts_voice,
                input=text,
                response_format="mp3",
            )
            audio_bytes = resp.read() if hasattr(resp, "read") else bytes(resp)
            if output_path:
                with open(output_path, "wb") as f:
                    f.write(audio_bytes)
            return audio_bytes
        except Exception as e2:
            _log_exception("TTS fallback 失败", e2)
            return None


def is_speech_available() -> bool:
    """语音是否已完整配置并可初始化客户端。"""
    return is_speech_ready() and bool(get_stt_client()) and bool(get_tts_client())


def transcribe_with_retry(
    audio_data: bytes,
    audio_format: str = "wav",
    max_retries: int = 2,
) -> Tuple[Optional[str], str]:
    """
    录音结束后自动 STT，带简单重试。
    返回 (识别文本, 错误说明)；成功时错误说明为空字符串。
    """
    if not is_speech_ready():
        return None, "语音未配置：请设置 SPEECH_API_KEY / STT_API_BASE / STT_MODEL / TTS_API_BASE / TTS_MODEL。"

    last_err = ""
    for attempt in range(max(1, max_retries)):
        try:
            text = speech_to_text(audio_data, audio_format=audio_format)
            if text and text.strip():
                return text.strip(), ""
            last_err = "识别结果为空，请重新录音或检查麦克风/环境噪音。"
        except Exception as e:
            _log_exception("STT 重试过程异常", e)
            last_err = f"识别异常: {type(e).__name__}: {e}"
        print(f"STT 重试 {attempt + 1}/{max_retries}: {last_err}")
    return None, last_err or "语音识别失败"
