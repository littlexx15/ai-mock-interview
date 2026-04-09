# -*- coding: utf-8 -*-
"""
AI 模拟面试器 - 主应用
Streamlit Web 界面：简历 + 可选作品集 + JD；仅语音面试；会话日志导出。
"""

import hashlib

import streamlit as st

from evaluation import evaluate_interview
from interview_engine import (
    add_record,
    advance_after_follow_up,
    build_interview_state,
    get_current_question,
    get_follow_up,
    interview_records_for_eval,
)
from jd_analyzer import analyze_match, generate_questions
from portfolio_parser import parse_portfolio
from resume_parser import parse_resume
from session_logger import (
    attach_final_report,
    log_to_json,
    log_to_markdown,
    new_interview_log,
    sync_qa_log_from_state,
)
from speech_service import (
    is_speech_available,
    text_to_speech,
    transcribe_with_retry,
)
from config_env import getenv_smart
from utils import score_dimension_label_zh, truncate_text


def _build_candidate_background_snippet(
    resume_summary: str,
    jd_text: str,
    portfolio_summary: str,
    job_title: str,
) -> str:
    """追问阶段轻量锚点：岗位 + 材料摘要 + JD 摘录（主问题仍由分析阶段完整生成）。"""
    parts = []
    if (job_title or "").strip():
        parts.append("目标岗位：" + job_title.strip())
    parts.append("简历摘要：" + truncate_text(resume_summary or "", 500))
    if (portfolio_summary or "").strip():
        parts.append("作品集摘要：" + truncate_text(portfolio_summary, 350))
    parts.append("JD 要点摘录：" + truncate_text(jd_text or "", 400))
    return "\n".join(parts)

st.set_page_config(
    page_title="AI 模拟面试器",
    page_icon="🎤",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    .main-header { font-size: 1.8rem; color: #1f77b4; margin-bottom: 1rem; }
</style>
""",
    unsafe_allow_html=True,
)


def init_session():
    if "resume_data" not in st.session_state:
        st.session_state.resume_data = None
    if "portfolio_data" not in st.session_state:
        st.session_state.portfolio_data = None
    if "jd_text" not in st.session_state:
        st.session_state.jd_text = ""
    if "match_analysis" not in st.session_state:
        st.session_state.match_analysis = None
    if "interview_state" not in st.session_state:
        st.session_state.interview_state = None
    if "eval_result" not in st.session_state:
        st.session_state.eval_result = None
    if "tts_cache" not in st.session_state:
        st.session_state.tts_cache = {}
    if "interview_log" not in st.session_state:
        st.session_state.interview_log = None


def _mode_label() -> str:
    """本应用仅支持语音模式（日志与展示用）。"""
    return "语音"


def _show_question_source_badge(q: dict) -> None:
    """展示本题 JD 主轴标签（来自出题 JSON 的 source 字段）。"""
    src = (q or {}).get("source")
    if not src:
        return
    labels = {
        "jd_core": "出题轴：JD 核心职责 / 必备能力",
        "jd_gap": "出题轴：JD 缺口 / 风险 / 能力迁移",
        "resume_evidence": "切入：简历案例 → 验证 JD 能力",
        "portfolio_evidence": "切入：作品案例 → 验证 JD 能力",
        "behavioral": "行为/情景题（应对齐 JD 软性要求）",
    }
    st.caption("📌 " + labels.get(str(src), str(src)))


def _md5_hex(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def _sync_interview_log():
    log = st.session_state.interview_log
    state = st.session_state.interview_state
    if not log or not state:
        return
    log["meta"]["mode"] = _mode_label()
    sync_qa_log_from_state(log, state, _mode_label())


def _sidebar_voice_notice():
    st.sidebar.header("🎙️ 面试方式")
    st.sidebar.caption("全程语音作答：录音结束自动识别并进入追问或下一题。")
    if not is_speech_available():
        st.sidebar.error(
            "⚠️ 语音不可用：请配置 OPENAI_API_KEY；若 LLM 使用 DeepSeek，请另设 SPEECH_API_BASE / SPEECH_API_KEY（见 .env.example）。"
        )


def _tts_play(text: str, cache_key: tuple):
    if cache_key in st.session_state.tts_cache:
        st.audio(st.session_state.tts_cache[cache_key], format="audio/mp3")
        return
    if st.button("🔊 播报题干", key=f"tts_{hash(cache_key)}"):
        with st.spinner("正在合成语音..."):
            audio_bytes = text_to_speech(text)
        if audio_bytes:
            st.session_state.tts_cache[cache_key] = audio_bytes
            st.audio(audio_bytes, format="audio/mp3")
        else:
            st.warning("语音合成失败，请检查 API 配置。")


def _apply_main_answer(state: dict, q_text: str, hint: str, answer: str) -> None:
    a = (answer or "").strip()
    if not a:
        return
    follow_up = get_follow_up(
        q_text,
        a,
        hint,
        candidate_background=state.get("candidate_background_snippet") or "",
        prior_records=state.get("records") or [],
        last_follow_up_question=state.get("_prev_follow_up_text") or "",
    )
    if follow_up and follow_up.upper() != "NEXT_QUESTION":
        state["follow_up_asked"] = True
        state["current_follow_up"] = follow_up
        state["last_answer"] = a
        state["_prev_follow_up_text"] = follow_up
    else:
        add_record(state, q_text, a)
        advance_after_follow_up(state)


def _apply_follow_answer(state: dict, q_text: str, follow_answer: str) -> None:
    fa = (follow_answer or "").strip()
    if not fa:
        return
    add_record(
        state,
        q_text,
        state.get("last_answer", ""),
        follow_up=state.get("current_follow_up", ""),
        follow_up_answer=fa,
    )
    advance_after_follow_up(state)


def _render_voice_turn(
    *,
    state: dict,
    role: str,
    q_text: str,
    hint: str,
    is_follow: bool,
) -> None:
    """
    语音模式单轮：开始录音 -> 录制结束自动 STT -> 自动提交引擎逻辑。
    不展示大字字幕；可选折叠查看转写（调试）。
    """
    idx = int(state["current_index"])
    arm_key = f"voice_arm_{idx}_{role}"
    proc_key = f"voice_done_hash_{idx}_{role}"

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🎙️ 开始录音", key=f"arm_{idx}_{role}"):
            st.session_state[arm_key] = True
            st.rerun()
    with col_b:
        if st.session_state.get(arm_key) and st.button("取消", key=f"cancel_{idx}_{role}"):
            st.session_state[arm_key] = False
            st.rerun()

    if not st.session_state.get(arm_key):
        st.info("点击「开始录音」后，再使用下方麦克风录制本题回答。")
        return

    st.caption("录制完成后将**自动识别并提交**，无需手动确认转写。")
    audio_file = None
    if hasattr(st, "audio_input"):
        audio_file = st.audio_input("结束录制即提交", key=f"audio_{idx}_{role}")
    else:
        audio_file = st.file_uploader(
            "上传录音",
            type=["wav", "mp3", "m4a", "webm", "ogg", "oga"],
            key=f"upload_{idx}_{role}",
        )

    if audio_file is None:
        return

    audio_bytes = audio_file.getvalue() if hasattr(audio_file, "getvalue") else audio_file.read()
    fn = getattr(audio_file, "name", "") or ""
    ext = fn.split(".")[-1].lower() if "." in fn else "wav"
    digest = _md5_hex(audio_bytes)

    if st.session_state.get(proc_key) == digest:
        return

    with st.spinner("正在识别语音…"):
        text, err = transcribe_with_retry(audio_bytes, audio_format=ext, max_retries=1)

    if not text:
        st.error(err or "识别失败")
        if st.button("🔄 重试本题录音", key=f"retry_{idx}_{role}"):
            st.session_state[proc_key] = None
            st.session_state[arm_key] = True
            st.rerun()
        return

    st.session_state[arm_key] = False
    st.success("已收到本题语音回答。")

    with st.expander("调试：查看识别文本（可选）", expanded=False):
        st.text(text)

    with st.spinner("正在生成追问或判定进入下一题…"):
        if not is_follow:
            _apply_main_answer(state, q_text, hint, text)
        else:
            _apply_follow_answer(state, q_text, text)

    st.session_state[proc_key] = digest
    _sync_interview_log()
    st.rerun()


def render_upload_section():
    st.header("📄 基础输入")
    c1, c2, c3 = st.columns(3)

    with c1:
        st.subheader("简历")
        up_r = st.file_uploader("PDF / DOCX / TXT", type=["pdf", "docx", "txt"], key="resume_upload")
        if up_r:
            sig = f"{up_r.name}:{getattr(up_r, 'size', 0)}"
            if st.session_state.get("_resume_sig") != sig:
                data = parse_resume(file_bytes=up_r.read(), filename=up_r.name)
                if data.get("error"):
                    st.error(data["error"])
                    st.session_state.resume_data = None
                else:
                    st.session_state.resume_data = data
                    st.session_state._resume_sig = sig
                    st.success(f"✅ 简历 {len(data['raw_text'])} 字")
            else:
                st.caption("简历已解析（未变更则不再重复解析）")
        else:
            st.session_state.resume_data = None
            st.session_state._resume_sig = None

    with c2:
        st.subheader("作品集（可选）")
        up_p = st.file_uploader("PDF / DOCX / TXT", type=["pdf", "docx", "txt"], key="portfolio_upload")
        if up_p:
            sigp = f"{up_p.name}:{getattr(up_p, 'size', 0)}"
            if st.session_state.get("_portfolio_sig") != sigp:
                pdata = parse_portfolio(file_bytes=up_p.read(), filename=up_p.name)
                if pdata.get("error"):
                    st.error(pdata["error"])
                    st.session_state.portfolio_data = None
                else:
                    st.session_state.portfolio_data = pdata
                    st.session_state._portfolio_sig = sigp
                    st.success(f"✅ 作品集 {len(pdata['raw_text'])} 字")
            else:
                st.caption("作品集已解析（未变更则不再重复解析）")
        else:
            st.session_state.portfolio_data = None
            st.session_state._portfolio_sig = None
            st.caption("未上传则分析仅基于简历+JD")

    with c3:
        st.subheader("岗位 JD")
        jd = st.text_area("粘贴 JD", height=180, placeholder="岗位职责、要求、加分项…", key="jd_input")
        st.session_state.jd_text = jd or ""

    return st.session_state.resume_data and st.session_state.jd_text.strip()


def render_analysis_section():
    if not st.session_state.resume_data or not st.session_state.jd_text.strip():
        return False

    st.header("📊 匹配分析与出题")
    if st.button("开始分析并生成面试问题", type="primary"):
        with st.spinner("分析中…"):
            resume = st.session_state.resume_data
            jd = st.session_state.jd_text
            p = st.session_state.portfolio_data
            p_raw = (p.get("raw_text") if p else "") or ""

            match = analyze_match(resume["raw_text"], jd, p_raw or None)
            st.session_state.match_analysis = match

            job_title = (match.get("job_title_guess") or "").strip() or "目标岗位"
            p_sum = (p.get("summary") if p else "") or ""
            r_sum = resume.get("summary", resume["raw_text"][:1500])
            cand_bg = _build_candidate_background_snippet(r_sum, jd, p_sum, job_title)

            questions = generate_questions(
                r_sum,
                jd,
                match,
                portfolio_summary=p_sum,
            )

            state = build_interview_state(
                questions,
                r_sum,
                jd,
                portfolio_summary=p_sum,
                job_title=job_title,
                candidate_background_snippet=cand_bg,
            )
            st.session_state.interview_state = state
            st.session_state.eval_result = None

            st.session_state.interview_log = new_interview_log(
                mode=_mode_label(),
                job_title=job_title,
                resume_summary=resume.get("summary", "")[:2000],
                portfolio_summary=p_sum[:2000] if p_sum else "",
                jd_text=jd,
                match_analysis=match,
                questions=questions,
            )
            _sync_interview_log()

        st.rerun()

    if st.session_state.match_analysis:
        ma = st.session_state.match_analysis
        ist = st.session_state.interview_state
        nq = len(ist["questions"]) if ist and ist.get("questions") else 0
        st.success(f"已生成 **{nq}** 道面试题。")
        st.markdown(f"**匹配摘要**：{ma.get('summary', '')}")
        with st.expander("查看完整匹配分析 JSON"):
            st.json(ma)
        return st.session_state.interview_state is not None

    return False


def render_interview_section():
    state = st.session_state.interview_state
    if not state:
        return

    st.header("🎤 模拟面试")
    idx = state["current_index"]
    total = len(state["questions"])
    current = get_current_question(state)

    if not current:
        state["phase"] = "evaluating"
        st.info("本轮面试题目已答完。")
        recs = interview_records_for_eval(state)
        qlen = len((st.session_state.interview_log or {}).get("qa_log") or [])
        print("[eval_btn] interview_done records=%s qa_log=%s" % (len(recs), qlen))
        if st.button("生成深度复盘报告", type="primary"):
            st.session_state.pop("eval_error", None)
            with st.spinner("评估中…"):
                _sync_interview_log()
                try:
                    print(
                        "[eval_btn] calling evaluate_interview records=%s summary_empty=%s jd_empty=%s"
                        % (
                            len(recs),
                            not (state.get("resume_summary") or "").strip(),
                            not (state.get("jd_text") or "").strip(),
                        )
                    )
                    ev = evaluate_interview(
                        state["resume_summary"],
                        state["jd_text"],
                        recs,
                        portfolio_summary=state.get("portfolio_summary", "") or "",
                    )
                    st.session_state.eval_result = ev
                    if st.session_state.interview_log:
                        attach_final_report(st.session_state.interview_log, ev)
                    print("[eval_btn] eval_result keys=%s" % list((ev or {}).keys())[:8])
                except Exception as ex:
                    st.session_state.eval_result = None
                    st.session_state["eval_error"] = str(ex)
                    print("[eval_btn] exception: %s" % ex)
            st.rerun()
        return

    q_text = current.get("question", "")
    q_type = current.get("type", "通用")
    hint = current.get("hint", "")
    _show_question_source_badge(current)

    if state.get("follow_up_asked"):
        # 追问轮必须展示「追问句」；若仍用主问题 q_text 作为大标题，用户会感觉「同一题问了两遍」
        st.markdown(f"**第 {idx + 1}/{total} 题 · 追问轮** · [{q_type}]")
        with st.expander("📌 回顾本题主问题", expanded=False):
            st.write(q_text)
        fu_display = (state.get("current_follow_up") or "").strip()
        st.info(f"**追问：**\n\n{fu_display}")
    else:
        st.markdown(f"**第 {idx + 1}/{total} 题 · 主问题** · [{q_type}]")
        st.info(q_text)

    if not is_speech_available():
        st.error(
            "无法进行语音面试：请检查 OPENAI_API_KEY；若聊天走 DeepSeek，语音需单独配置 SPEECH_API_BASE（如 OpenAI 官方）与 SPEECH_API_KEY。"
        )
        return

    if state.get("follow_up_asked"):
        _tts_play(state.get("current_follow_up", ""), (idx, "fu", state.get("current_follow_up", "")))
    else:
        _tts_play(q_text, (idx, "q", q_text))

    if not state.get("follow_up_asked"):
        _render_voice_turn(
            state=state,
            role="main",
            q_text=q_text,
            hint=hint,
            is_follow=False,
        )
    else:
        _render_voice_turn(
            state=state,
            role="follow",
            q_text=q_text,
            hint=hint,
            is_follow=True,
        )


def render_evaluation_section():
    err = st.session_state.get("eval_error")
    if err:
        st.error("深度复盘生成失败：%s" % err)

    ev = st.session_state.eval_result
    if not ev:
        return

    st.header("📋 深度复盘报告")

    st.markdown("### 总评")
    st.write(ev.get("overall_comment", ""))

    st.markdown("### 维度评分")
    scores = ev.get("scores") or {}
    for k, v in scores.items():
        st.metric(score_dimension_label_zh(k), f"{v}/10")

    st.markdown("### 回答质量备注")
    aq = ev.get("answer_quality_notes") or {}
    if aq.get("vague_or_jargon"):
        st.write("**空泛/术语堆砌**")
        for x in aq["vague_or_jargon"]:
            st.write(f"- {x}")
    if aq.get("off_topic"):
        st.write("**跑题**")
        for x in aq["off_topic"]:
            st.write(f"- {x}")

    st.markdown("### 逐题复盘")
    for pq in ev.get("per_question_reviews") or []:
        with st.expander(f"第 {pq.get('question_index', '?')} 题：{truncate_text(pq.get('question', ''), 60)}"):
            st.write("**考察意图**：", pq.get("interviewer_intent", ""))
            st.write("**亮点**：", pq.get("strengths", ""))
            st.write("**问题**：", pq.get("issues", ""))
            wp = pq.get("weak_phrases") or []
            if wp:
                st.write("**欠佳表述**：", ", ".join(wp))
            st.write("**可补充**：", pq.get("add_examples", ""))
            st.write("**更好说法（口语）**：", pq.get("better_phrasing_spoken", ""))

    st.markdown("### 话术优化（现场怎么说）")
    for item in ev.get("oral_rewrites") or []:
        if isinstance(item, dict):
            st.write(f"- ❌ 避免：{item.get('dont_say', '')}")
            st.write(f"  ✅ 建议：{item.get('say_instead', '')}")

    st.markdown("### 不建议这么说")
    for s in ev.get("do_not_say") or []:
        st.write(f"- {s}")

    st.markdown("### 风险提醒")
    for s in ev.get("risk_reminders") or []:
        st.write(f"- {s}")

    st.markdown("### 改进建议")
    for s in ev.get("improvement_suggestions") or []:
        st.write(f"• {s}")

    st.markdown("### 表达优化对照")
    for item in ev.get("optimized_expressions") or []:
        if isinstance(item, dict):
            st.write(f"- 原：{item.get('original', '')}")
            st.write(f"  改：{item.get('suggested', '')}")

    st.markdown("### 练习建议")
    for s in ev.get("next_practice") or []:
        st.write(f"• {s}")

    log = st.session_state.interview_log
    if log:
        st.subheader("📎 本次面试日志")
        _sync_interview_log()
        j = log_to_json(log)
        m = log_to_markdown(log)
        c1, c2, c3 = st.columns(3)
        with c1:
            st.download_button("下载 JSON", j, file_name="interview_log.json", mime="application/json")
        with c2:
            st.download_button("下载 Markdown", m, file_name="interview_log.md", mime="text/markdown")
        with c3:
            st.download_button("下载 TXT", m, file_name="interview_log.txt", mime="text/plain")
        with st.expander("在页面中查看完整日志 JSON"):
            st.code(j, language="json")


def main():
    init_session()

    st.markdown('<p class="main-header">🎤 AI 模拟面试器</p>', unsafe_allow_html=True)
    st.caption("简历 + 可选作品集 + JD → 匹配分析 → 语音模拟面试 → 深度复盘与日志导出。")

    _sidebar_voice_notice()

    if not getenv_smart("OPENAI_API_KEY"):
        st.warning("⚠️ 请配置 OPENAI_API_KEY（本地用 `.env`，云端用平台 Secrets / 环境变量）")

    if not render_upload_section():
        st.stop()

    if not render_analysis_section() and not st.session_state.interview_state:
        st.stop()

    render_interview_section()
    render_evaluation_section()


if __name__ == "__main__":
    main()
