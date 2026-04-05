# AI 模拟面试器

本地可运行的 Web 应用：上传**简历**、可选**作品集**、粘贴 **JD**，进行匹配分析与**仅语音**模拟面试。**出题以 JD 为主轴**，简历/作品作为证据与缺口来源；输出**深度复盘**并支持**完整面试日志**导出（JSON / Markdown / TXT）。

---

## 一、产品能力（当前版本）

### 1.1 核心流程

1. 上传简历（PDF/DOCX/TXT）
2. 可选上传作品集（PDF/DOCX/TXT，文本提取）
3. 粘贴 JD
4. 点击「开始分析并生成面试问题」→ 查看匹配摘要与题目数量（**分析仅在你点击按钮时执行一次**，结果缓存在会话中）
5. 语音逐题作答（支持追问）
6. 结束后点击「生成深度复盘报告」（**完整复盘仅在最后一步执行**，不阻塞单题）
7. 查看报告；下载本次**面试日志**（含输入摘要、匹配分析、全量问答、最终评价）

### 1.2 语音面试

- 可选 **播报题干**（TTS）
- **开始录音** → 录制结束 → **自动语音识别** → **生成追问或进入下一题**（界面有进度提示）
- 同一份上传文件在页面刷新/重跑时**不会重复解析**（文件名+大小未变则跳过）
- 识别失败时提示错误，支持**重试本题录音**

### 1.3 深度复盘（evaluation）

结合**简历摘要、作品集摘要（若有）、JD、实际问答记录**，输出：

- 多维度评分（含 JD 相关性、与简历/作品一致性、清晰度、具体度、说服力、岗位感等）
- **逐题复盘**（考察意图、亮点、问题、更好口语表达）
- **话术优化**（不要这么说 / 可以怎么说）
- **风险提醒**与改进建议

### 1.4 预留 / 后续可优化

| 项目 | 说明 |
|------|------|
| 作品集/简历 **图片 OCR** | `portfolio_parser.parse_portfolio_image`、`resume_parser.parse_resume_image` 已预留 |
| **实时流式**语音 | 仍为录完再识别，非 WebSocket 实时通话 |
| 部分兼容 API 对 `verbose_json` STT | `speech_service` 内已做回退处理 |

---

## 二、技术栈与模块

- **前端**：Streamlit（建议 ≥1.32，支持 `st.audio_input`）
- **Python**：3.8+
- **LLM**：OpenAI 兼容 API

| 模块 | 职责 |
|------|------|
| `app.py` | 页面流程、双模式、日志同步与下载 |
| `portfolio_parser.py` | 作品集解析（MVP：复用简历解析逻辑） |
| `session_logger.py` | 会话日志结构、同步、JSON/Markdown 导出 |
| `jd_analyzer.py` | 简历+可选作品集+JD 匹配分析与出题 |
| `interview_engine.py` | 面试状态、追问、记录（统一 `answer` 文本） |
| `evaluation.py` | 深度复盘与结构化结果 |
| `speech_service.py` | STT/TTS、带重试的 `transcribe_with_retry` |
| `prompts.py` | 联合分析、出题、深度评价等 Prompt |
| `resume_parser.py` | 简历解析 |
| `llm_service.py` | LLM 调用 |
| `config_env.py` | 环境变量与 Streamlit Secrets 统一读取 |
| `utils.py` | 工具函数 |

---

## 三、环境变量

在 `.env` 中配置（可复制 `.env.example`）：

- `OPENAI_API_KEY`（必填）
- `OPENAI_API_BASE`（可选，兼容网关）
- `LLM_MODEL`（可选，默认见 `llm_service.py`）
- `OPENAI_TIMEOUT`（可选，HTTP 超时秒数，默认 `120`，网络慢或网关易超时时可调大）
- 语音可选：`STT_MODEL`、`TTS_MODEL`、`TTS_VOICE`

---

## 四、如何运行

```bash
cd ai-mock-interview
pip install -r requirements.txt
copy .env.example .env
# 编辑 .env 填入 OPENAI_API_KEY 等

streamlit run app.py
```

浏览器访问 `http://localhost:8501`。

---

## 五、公网部署

详见 **[DEPLOYMENT.md](DEPLOYMENT.md)**（推荐 **Streamlit Community Cloud**；亦说明 Render/Railway 启动方式与超时风险）。

要点：在平台配置与 `.env` 同名的 `OPENAI_API_KEY` 等；**不要**把真实 `.env` 提交到仓库。

---

## 六、目录结构（节选）

```
ai-mock-interview/
├── app.py
├── portfolio_parser.py
├── session_logger.py
├── resume_parser.py
├── jd_analyzer.py
├── interview_engine.py
├── evaluation.py
├── speech_service.py
├── prompts.py
├── llm_service.py
├── config_env.py
├── utils.py
├── requirements.txt
├── Procfile
├── runtime.txt
├── .env.example
├── .streamlit/
│   └── config.toml
├── DEPLOYMENT.md
└── README.md
```

---

## 七、常见问题

**Q：没有作品集能否使用？**  
A：可以。分析 Prompt 会自动降级为仅简历+JD。

**Q：语音失败会崩页面吗？**  
A：会提示错误并支持重试；请检查网络与 OPENAI_API_KEY，或稍后再试。

**Q：如何用国产大模型？**  
A：设置 `OPENAI_API_BASE` 与对应 `OPENAI_API_KEY`、`LLM_MODEL`。若网关不支持部分音频接口，语音功能可能不可用。

**Q：面试日志存在哪里？**  
A：运行期间在 `st.session_state["interview_log"]`；结束后可通过页面按钮下载 JSON/Markdown/TXT。
