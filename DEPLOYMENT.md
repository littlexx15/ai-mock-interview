# 部署说明（Streamlit）

## 最推荐：Streamlit Community Cloud

**原因简述**

- 官方为 Streamlit 优化，连接 GitHub 即可部署，无需自己写 Dockerfile（除非需要系统依赖）。
- 密钥通过 **App settings → Secrets** 管理，与代码分离，避免把 `.env` 提交进仓库。
- 本项目为纯 Streamlit + OpenAI API，无自建数据库，与 Cloud 模型匹配。

**Render / Railway** 也可用：用下方「通用启动命令」以容器或 Web Service 运行；需自行配置环境变量，并注意免费档 **HTTP 超时** 往往短于一次长 LLM 调用（见下文风险）。

---

## 主要风险点

| 风险 | 说明 |
|------|------|
| **密钥泄露** | 切勿将真实 `.env` 或含 API Key 的 `.streamlit/secrets.toml` 提交到 Git。仓库内仅保留 `.env.example`。 |
| **长请求 / 超时** | `evaluation.py` 等会使用较大 `max_tokens`（如终评），一次调用可能持续数十秒到数分钟；**免费托管** 的反向代理常有 **60s～120s** 级超时，可能导致页面报错或中断。缓解：换更快模型、适当减小输出、或升级付费档 / 自托管。 |
| **冷启动** | 免费实例闲置后会休眠，首次访问需等待数秒～数十秒。 |
| **上传体积** | `.streamlit/config.toml` 中 `maxUploadSize` 可按需调整；超大 PDF 解析会占用内存。 |
| **出站网络** | 需能访问你配置的 OpenAI 兼容 API（含 `OPENAI_API_BASE` 代理）；部分区域需合规线路。 |

---

## 环境变量（与本地 `.env` 键名一致）

| 变量 | 必填 | 说明 |
|------|------|------|
| `OPENAI_API_KEY` | 是 | LLM / 语音 API 密钥 |
| `OPENAI_API_BASE` | 否 | 兼容 API 基地址（Azure/自建网关等） |
| `LLM_MODEL` | 否 | 默认 `deepseek-chat`（可改为 `gpt-4o-mini` 等） |
| `OPENAI_TIMEOUT` | 否 | 秒，默认 `120` |
| `STT_MODEL` | 否 | 默认 `whisper-1` |
| `TTS_MODEL` / `TTS_VOICE` | 否 | TTS 模型与音色 |

**Streamlit Cloud**：在 **Secrets** 中用 TOML 写入，例如：

```toml
OPENAI_API_KEY = "sk-..."
# OPENAI_API_BASE = "https://..."
# LLM_MODEL = "deepseek-chat"
```

**Render / Railway**：在 Environment 里逐条添加同名变量。

---

## 仓库布局

- 若 **整个仓库根目录就是本项目**（含 `app.py`、`requirements.txt`），按各平台默认即可。
- 若本项目在 **子目录** `ai-mock-interview/`，Streamlit Cloud 需在设置里把 **Main file path** 设为 `ai-mock-interview/app.py`，并把 **Root path** 指到该子目录或调整「Python 包根」；Render/Railway 的 **Root Directory** 设为 `ai-mock-interview`。

---

## 启动命令（Render / Railway / 通用）

```bash
streamlit run app.py --server.port=$PORT --server.address=0.0.0.0
```

Windows 本地测试公网绑定可设 `set PORT=8501` 后执行（PowerShell 用 `$env:PORT=8501`）。

项目根目录已提供 `Procfile`（供 Railway/Heroku 风格平台识别 `web` 进程）。

---

## 本地路径与临时文件

- 简历/作品集解析使用上传字节与内存，**无强制写磁盘**；TTS 仅在传入 `output_path` 时写文件（当前主流程未依赖）。
- 代码中 **无** 写死的 `C:\` / `D:\` 等业务路径；部署时工作目录为应用根即可。

---

## requirements.txt

部署环境只需 `pip install -r requirements.txt`。已移除未使用的 `pydantic` 依赖以减小镜像体积。

可选：在平台支持时添加 `runtime.txt` 固定 Python 版本，例如：

```
python-3.11.9
```

（文件名与格式以各平台文档为准。）
