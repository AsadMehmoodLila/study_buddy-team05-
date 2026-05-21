"""
Study Buddy — Professional AI Study Assistant
=============================================
Main Streamlit application entry-point.
"""

import base64
import json
import time
from html import escape
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils import (
    add_task,
    build_context_block,
    chat_with_documents,
    complete_task,
    extract_documents,
    generate_short_summary,
    generate_detailed_summary,
    generate_flashcards,
    generate_notes,
    generate_quiz,
    generate_study_roadmap,
    load_productivity,
    load_progress,
    log_pomodoro_session,
    normalize_task_priorities,
    save_progress,
    update_task_priority,
)

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Study Buddy — AI Study Assistant",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS injection ──────────────────────────────────────────────────────────────
def load_css() -> None:
    css_path = Path("assets/style.css")
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)


# ── Session state defaults ─────────────────────────────────────────────────────
def ensure_session_defaults() -> None:
    defaults = {
        "documents": [],
        "document_context": "",
        "summaries": {},
        "roadmap": [],
        "doc_messages": [],
        "home_fc_cards": [],
        "home_fc_index": 0,
        "home_fc_flipped": False,
        "home_quiz_data": [],
        "home_quiz_submitted": False,
        "quiz": [],
        "quiz_topic": "",
        "quiz_submitted": False,
        "pomodoro_running": False,
        "pomodoro_end_time": None,
        "pomodoro_mode": "focus",
    }
    for key, val in defaults.items():
        st.session_state.setdefault(key, val)


def has_documents() -> bool:
    return bool(st.session_state.get("document_context"))


# ── Document caching ──────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def parse_uploaded_documents(file_payloads: tuple) -> list:
    """Cache extraction by (name, mime_type, bytes) tuple."""
    normalized = [
        {"name": n, "type": t, "bytes": b}
        for n, t, b in file_payloads
    ]
    return extract_documents(normalized)


# ── Helpers ────────────────────────────────────────────────────────────────────
def render_metric_card(label: str, value, note: str) -> None:
    st.markdown(
        f"""
        <div class="metric-card animate-in">
            <span>{label}</span>
            <strong>{value}</strong>
            <small>{note}</small>
        </div>
        """,
        unsafe_allow_html=True,
    )


def file_icon_class(filename: str) -> tuple[str, str]:
    """Return (emoji, css-class) based on extension."""
    ext = Path(filename).suffix.lower()
    mapping = {
        ".pdf":  ("📄", "doc-file-icon-pdf"),
        ".txt":  ("📝", "doc-file-icon-txt"),
        ".md":   ("📋", "doc-file-icon-md"),
        ".pptx": ("📊", "doc-file-icon-pptx"),
    }
    return mapping.get(ext, ("📁", "doc-file-icon-txt"))


def render_doc_selector(key_suffix: str = "") -> bool:
    """Toggle for grounding AI answers in uploaded documents."""
    if not has_documents():
        return False
    return st.toggle(
        "Ground answers in uploaded documents",
        value=True,
        help="When enabled, Study Buddy answers strictly from your uploaded files.",
        key=f"doc_toggle_{key_suffix}",
    )


def page_header(icon: str, title: str, subtitle: str = "") -> None:
    st.markdown(
        f"""
        <div class="page-header animate-in">
            <h2>{icon}&nbsp; {title}</h2>
            {"<p>" + subtitle + "</p>" if subtitle else ""}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Initialise ─────────────────────────────────────────────────────────────────
load_css()
ensure_session_defaults()

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        """
        <div style="padding:1rem 0 0.5rem; text-align:center;">
            <div style="font-size:2.2rem;">🎓</div>
            <div style="font-weight:800;font-size:1.1rem;letter-spacing:0;color:#111827;">
                Study Buddy
            </div>
            <div style="font-size:0.72rem;color:#64748b;margin-top:0.2rem;
                        text-transform:uppercase;letter-spacing:0.1em;">
                AI Study Assistant
            </div>
        </div>
        <hr style="border-color:rgba(99,179,237,0.12);margin:0.5rem 0 1rem;">
        """,
        unsafe_allow_html=True,
    )

    page = st.radio(
        "Navigate",
        [
            "🏠  Home",
            "📁  Document Hub",
            "❓  Quiz",
            "🗺️  Smart Sequence",
            "✅  Task Manager",
            "⏱️  Pomodoro Timer",
            "📊  Progress",
        ],
        label_visibility="collapsed",
    )

    st.markdown("<hr style='border-color:rgba(99,179,237,0.12);margin:0.75rem 0;'>", unsafe_allow_html=True)
    st.markdown("<p style='font-size:0.7rem;text-transform:uppercase;letter-spacing:0.1em;color:#64748b;margin-bottom:0.5rem;'>Document Memory</p>", unsafe_allow_html=True)

    if has_documents():
        doc_count = len(st.session_state.documents)
        st.success(f"✅ {doc_count} file{'s' if doc_count != 1 else ''} loaded & ready")
    else:
        st.info("📤 Upload files in Document Hub")

# Strip the emoji prefix to get the clean page name
page_name = page.split("  ", 1)[-1] if "  " in page else page


# ══════════════════════════════════════════════════════════════════════════════
#  HOME PAGE
# ══════════════════════════════════════════════════════════════════════════════
if page_name == "Home":
    # ── Hero banner ──────────────────────────────────────────────────────────
    st.markdown(
        """
        <section class="hero animate-in">
            <div class="hero-content">
                <p class="eyebrow">✨ AI-Powered Study Workspace</p>
                <h1>Study Buddy</h1>
                <p>
                    Upload your notes, generate intelligent summaries, test yourself
                    with adaptive quizzes, and build a personalised learning path —
                    all powered by AI.
                </p>
                <div class="hero-badges">
                    <span class="hero-badge">🤖 AI-Generated Notes</span>
                    <span class="hero-badge">🃏 Smart Flashcards</span>
                    <span class="hero-badge">📝 Adaptive Quizzes</span>
                    <span class="hero-badge">🗺️ Study Roadmaps</span>
                </div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    # ── Feature cards row ────────────────────────────────────────────────────
    st.markdown(
        """
        <div class="section-label">What do you want to do today?</div>
        """,
        unsafe_allow_html=True,
    )

    feat_col1, feat_col2, feat_col3 = st.columns(3, gap="medium")
    with feat_col1:
        st.markdown(
            """
            <div class="feature-card" style="min-height: 210px;">
                <div class="feature-icon feature-icon-blue">📝</div>
                <h3>Generate Study Notes</h3>
                <p>Get AI-structured notes with key points and summaries on any topic or from your uploaded documents.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with feat_col2:
        st.markdown(
            """
            <div class="feature-card" style="min-height: 210px;">
                <div class="feature-icon feature-icon-purple">🃏</div>
                <h3>Flashcard Deck</h3>
                <p>Slide through AI-generated flashcards for active recall — flip to reveal answers instantly.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with feat_col3:
        st.markdown(
            """
            <div class="feature-card" style="min-height: 210px;">
                <div class="feature-icon feature-icon-cyan">❓</div>
                <h3>Quick Quiz</h3>
                <p>Test yourself with a 3-question multiple-choice quiz directly from this page — no page switching needed.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<hr style='border-color:rgba(99,179,237,0.1);margin:1.5rem 0;'>", unsafe_allow_html=True)

    # ── SECTION 1: Generate Notes ─────────────────────────────────────────────
    st.markdown('<div class="section-label">📝 &nbsp;Study Notes Generator</div>', unsafe_allow_html=True)
    
    notes_topic = st.text_input(
        "Topic to learn",
        placeholder="e.g. Photosynthesis, World War II, Calculus…",
        key="home_notes_topic",
    )
    diff_col, btn_col = st.columns([1, 1])
    with diff_col:
        notes_diff = st.selectbox(
            "Difficulty level",
            ["Beginner", "Intermediate", "Advanced"],
            index=1,
            key="home_notes_diff",
        )
    with btn_col:
        use_docs_notes = render_doc_selector("notes")

    if st.button("✨ Generate Notes", use_container_width=True, key="gen_notes_btn"):
        if not notes_topic.strip() and not use_docs_notes:
            st.warning("Enter a topic or upload documents first.")
        else:
            ctx = st.session_state.document_context if use_docs_notes else None
            with st.spinner("Generating intelligent notes…"):
                result = generate_notes(notes_topic, difficulty=notes_diff, source_context=ctx)
            st.session_state["home_notes_result"] = result
            st.session_state["home_notes_topic_display"] = notes_topic or "Uploaded Documents"
            st.session_state["home_notes_used_docs"] = use_docs_notes
            # Clear previous flashcards/quiz when generating new notes
            st.session_state.home_fc_cards = []
            st.session_state.home_quiz_data = []

    # Display notes result
    if "home_notes_result" in st.session_state:
        result = st.session_state["home_notes_result"]
        st.markdown(
            f"""
            <div class="glass-card animate-in" style="margin-top:1rem;">
                <div style="font-size:0.7rem;text-transform:uppercase;letter-spacing:0.1em;
                            color:#64748b;font-weight:700;margin-bottom:0.75rem;">
                    📝 Notes — {st.session_state.get('home_notes_topic_display','Topic')}
                </div>
            """,
            unsafe_allow_html=True,
        )
        st.info(result.get("notes", "No notes generated."))

        if result.get("points"):
            st.markdown("**🔑 Key Points**")
            for pt in result["points"]:
                st.markdown(f"&nbsp;&nbsp;• {pt}")

        if result.get("summary"):
            st.success(f"**📋 Summary:** {result['summary']}")

        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<hr style='border-color:rgba(99,179,237,0.1);margin:1.5rem 0;'>", unsafe_allow_html=True)
        st.markdown('<div class="section-label">🎓 &nbsp;Deepen Your Learning</div>', unsafe_allow_html=True)
        
        btn_c1, _ = st.columns([1, 2])
        with btn_c1:
            if st.button("🃏 Generate Flashcards", use_container_width=True):
                topic = st.session_state.get("home_notes_topic_display")
                ctx = st.session_state.document_context if st.session_state.get("home_notes_used_docs") else None
                with st.spinner("Creating your flashcard deck…"):
                    cards = generate_flashcards(topic, source_context=ctx)
                st.session_state.home_fc_cards = cards
                st.session_state.home_fc_index = 0
                st.session_state.home_fc_flipped = False
       

    # Render slide-based flashcard viewer if they exist
    cards = st.session_state.get("home_fc_cards", [])
    if cards:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-label">🃏 &nbsp;Flashcard Deck</div>', unsafe_allow_html=True)
        idx = st.session_state.home_fc_index
        card = cards[idx]
        flipped = st.session_state.home_fc_flipped
        total = len(cards)

        flip_class = "flipped" if flipped else ""
        if isinstance(card, dict):
            # AI ne lowercase, uppercase ya koi aur key di ho, yeh sab handle kar lega
            front_text = card.get("question", card.get("Question", card.get("front", "⚠️ Formatting error from AI")))
            back_text  = card.get("answer", card.get("Answer", card.get("back", "Please generate the flashcards again.")))
        else:
            # Agar AI ne dictionary ke bajaye kuch aur hi bhej diya ho
            front_text = "⚠️ AI Response Error"
            back_text  = str(card)

        st.markdown(
            f"""
            <div class="flashcard-container animate-in" onclick="" id="flashcard_wrap">
                <div class="flashcard-inner {flip_class}" id="fc_inner">
                    <div class="flashcard-front">
                        <div class="flashcard-label">Question</div>
                        <div class="flashcard-text">{front_text}</div>
                        <div class="flashcard-counter">{idx + 1} of {total}</div>
                    </div>
                    <div class="flashcard-back">
                        <div class="flashcard-label">Answer</div>
                        <div class="flashcard-text">{back_text}</div>
                        <div class="flashcard-counter">{idx + 1} of {total}</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        nav_l, flip_c, nav_r = st.columns([1, 2, 1])
        with nav_l:
            if st.button("⬅ Prev", use_container_width=True, key="fc_prev", disabled=(idx == 0)):
                st.session_state.home_fc_index = max(0, idx - 1)
                st.session_state.home_fc_flipped = False
                st.rerun()
        with flip_c:
            flip_label = "👁 Show Answer" if not flipped else "🔄 Show Question"
            if st.button(flip_label, use_container_width=True, key="fc_flip"):
                st.session_state.home_fc_flipped = not flipped
                st.rerun()
        with nav_r:
            if st.button("Next ➡", use_container_width=True, key="fc_next", disabled=(idx == total - 1)):
                st.session_state.home_fc_index = min(total - 1, idx + 1)
                st.session_state.home_fc_flipped = False
                st.rerun()

        st.progress((idx + 1) / total, text=f"Card {idx + 1} of {total}")

    

# ══════════════════════════════════════════════════════════════════════════════
#  DOCUMENT HUB
# ══════════════════════════════════════════════════════════════════════════════
elif page_name == "Document Hub":
    page_header("📁", "Document Hub", "Upload and manage your study materials — PDFs, text files, markdown notes, and PowerPoint decks.")

    uploaded_files = st.file_uploader(
        "Drop files here or click to upload",
        type=["pdf", "txt", "md", "pptx"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    if uploaded_files:
        payloads = tuple(
            (f.name, f.type, f.getvalue())
            for f in uploaded_files
        )
        with st.spinner("📖 Extracting document text…"):
            st.session_state.documents = parse_uploaded_documents(payloads)
            st.session_state.document_context = build_context_block(st.session_state.documents)

    documents = st.session_state.documents

    if documents:
        # ── Metrics row ───────────────────────────────────────────────────────
        total_words = sum(d["word_count"] for d in documents)
        total_chars = sum(d["char_count"] for d in documents)

        m1, m2, m3 = st.columns(3, gap="medium")
        with m1:
            render_metric_card("📄 Files Loaded", len(documents), "ready for AI analysis")
        with m2:
            render_metric_card("📝 Total Words", f"{total_words:,}", "extracted text")
        with m3:
            render_metric_card("💾 Characters", f"{total_chars:,}", "cached context")

        # ── Aligned file list ─────────────────────────────────────────────────
        st.markdown("<div class='section-label' style='margin-top:1.5rem;'>Uploaded Files</div>", unsafe_allow_html=True)
        st.markdown('<div class="doc-file-list">', unsafe_allow_html=True)

        for doc in documents:
            icon, icon_cls = file_icon_class(doc["name"])
            status_html = (
                '<span class="doc-status-badge doc-status-ready">✓ Ready</span>'
                if doc["text"]
                else '<span class="doc-status-badge doc-status-error">⚠ Error</span>'
            )
            words = f"{doc['word_count']:,} words"
            st.markdown(
                f"""
                <div class="doc-file-item">
                    <div class="doc-file-icon {icon_cls}">{icon}</div>
                    <div>
                        <div class="doc-file-name">{doc['name']}</div>
                        <div class="doc-file-meta">{words}</div>
                    </div>
                    {status_html}
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)

       # ── Per-document expanders ────────────────────────────────────────────
        st.markdown("<div class='section-label' style='margin-top:1.5rem;'>File Details & Summaries</div>", unsafe_allow_html=True)
        for doc in documents:
            icon, _ = file_icon_class(doc["name"])
            status = "Ready" if doc["text"] else "Needs attention"
            with st.expander(f"{icon} {doc['name']}  •  {status}", expanded=not doc["text"]):
                if doc["error"]:
                    st.warning(doc["error"])

                m1, m2 = st.columns(2)
                with m1:
                    st.metric("Word Count", f"{doc['word_count']:,}")
                with m2:
                    st.metric("Characters", f"{doc['char_count']:,}")

                # Calls the short summary function
                if doc["text"] and st.button(f"📝 Generate File Summary", key=f"btn_sum_{doc['name']}"):
                    with st.spinner("Generating brief summary…"):
                        st.session_state.summaries[doc["name"]] = generate_short_summary(doc["name"], doc["text"])

                if st.session_state.summaries.get(doc["name"]):
                    st.markdown("**📑 Brief Summary**")
                    st.info(st.session_state.summaries[doc["name"]])

        # ── Bulk actions ──────────────────────────────────────────────────────
        st.markdown("<hr style='border-color:rgba(99,179,237,0.1);'>", unsafe_allow_html=True)
        
        # Initialize dictionary for detailed summaries if not exists
        if "detailed_summaries" not in st.session_state:
            st.session_state.detailed_summaries = {}

        bulk_col1, bulk_col2 = st.columns(2, gap="medium")
        with bulk_col1:
            if st.button("📑 Generate All Detailed Summaries", use_container_width=True):
                with st.spinner("Reading and generating detailed explanations for all files…"):
                    for doc in documents:
                        if doc["text"]:
                            # Always forces a new detailed summary generation
                            st.session_state.detailed_summaries[doc["name"]] = generate_detailed_summary(doc["name"], doc["text"])
                st.session_state.show_all_summaries = True 
                st.success("All detailed summaries successfully generated!")
                
        with bulk_col2:
            if st.button("🗑️ Clear Document Workspace", use_container_width=True):
                st.session_state.documents = []
                st.session_state.document_context = ""
                st.session_state.summaries = {}
                st.session_state.detailed_summaries = {}
                st.session_state.roadmap = []
                st.session_state.doc_messages = []
                st.session_state.show_all_summaries = False
                st.rerun()

        # ── Combined Summaries Display ──────────────────────────
        if st.session_state.get("show_all_summaries") and st.session_state.get("detailed_summaries"):
            st.markdown("<div class='section-label' style='margin-top:1.5rem;'>📑 Combined Detailed Summaries</div>", unsafe_allow_html=True)
            
            combined_text = ""
            for doc_name, summary in st.session_state.detailed_summaries.items():
                combined_text += f"**📄 {doc_name}**\n\n{summary}\n\n---\n\n"
            
            st.info(combined_text)

        # ── Combined Summaries Display (Single Flow) ──────────────────────────
        if st.session_state.get("show_all_summaries") and st.session_state.summaries:
            st.markdown("<div class='section-label' style='margin-top:1.5rem;'>📑 Combined Document Summaries</div>", unsafe_allow_html=True)
            
            combined_text = ""
            for doc_name, summary in st.session_state.summaries.items():
                combined_text += f"**📄 {doc_name}**\n{summary}\n\n---\n\n"
            
            st.info(combined_text)            

        # ── Chat with docs ────────────────────────────────────────────────────
        st.markdown("<div class='section-label' style='margin-top:1.5rem;'>💬 Chat with Your Documents</div>", unsafe_allow_html=True)
        st.caption("AI answers are grounded strictly in your uploaded context.")

        for msg in st.session_state.doc_messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        question = st.chat_input("Ask a question about your documents…")
        if question:
            st.session_state.doc_messages.append({"role": "user", "content": question})
            with st.chat_message("user"):
                st.write(question)
            with st.chat_message("assistant"):
                with st.spinner("Searching your notes…"):
                    answer = chat_with_documents(question, st.session_state.document_context)
                    st.write(answer)
            st.session_state.doc_messages.append({"role": "assistant", "content": answer})

    else:
        st.markdown(
            """
            <div class="glass-card animate-in" style="text-align:center;padding:3rem;">
                <div style="font-size:3rem;margin-bottom:1rem;">📤</div>
                <h3 style="margin:0 0 0.5rem;">No documents uploaded yet</h3>
                <p style="color:#64748b;max-width:420px;margin:0 auto;">
                    Upload PDFs, text files, Markdown notes, or PowerPoint decks above.
                    Study Buddy extracts and caches the text for AI analysis throughout your session.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
#  QUIZ  (full dedicated page)
# ══════════════════════════════════════════════════════════════════════════════
elif page_name == "Quiz":
    page_header("❓", "Quiz", "Test your knowledge with AI-generated multiple-choice questions.")

    st.markdown("Upload a document to generate a quiz directly from it.")
    uploaded_files = st.file_uploader(
        "Upload files for quiz",
        type=["pdf", "txt", "md", "pptx"],
        accept_multiple_files=True,
        label_visibility="collapsed",
        key="quiz_file_uploader",
    )

    if st.button("🚀 Generate Quiz", use_container_width=True, key="gen_quiz_main"):
        if not uploaded_files:
            st.warning("Please upload a document first.")
        else:
            payloads = tuple((f.name, f.type, f.getvalue()) for f in uploaded_files)
            with st.spinner("Extracting text and crafting quiz questions…"):
                docs = parse_uploaded_documents(payloads)
                ctx = build_context_block(docs)
                st.session_state.quiz = generate_quiz("Uploaded documents", source_context=ctx)
                st.session_state.quiz_topic = "Uploaded documents"
                st.session_state.quiz_submitted = False

    if st.session_state.quiz:
        st.markdown("<div class='section-label' style='margin-top:1rem;'>Your Quiz</div>", unsafe_allow_html=True)
        score = 0
        quiz = st.session_state.quiz

        for i, q in enumerate(quiz):
            st.markdown(
                f"""
                <div class="quiz-question animate-in">
                    <div style="font-size:0.7rem;text-transform:uppercase;letter-spacing:0.1em;
                                color:#64748b;font-weight:700;margin-bottom:0.4rem;">
                        Question {i + 1}
                    </div>
                    <strong style="font-size:1rem;">{q['question']}</strong>
                </div>
                """,
                unsafe_allow_html=True,
            )
            ans = st.radio(
                f"Answer Q{i + 1}",
                q["options"],
                key=f"quiz_main_{i}",
                label_visibility="collapsed",
            )
            if ans == q["answer"]:
                score += 1

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("✅ Submit Quiz & Save Score", use_container_width=True, key="submit_quiz_main"):
            st.session_state.quiz_submitted = True
            save_progress(st.session_state.quiz_topic, score)

        if st.session_state.get("quiz_submitted"):
            pct = int((score / len(quiz)) * 100)
            color = "#0f766e" if pct >= 70 else "#d97706" if pct >= 40 else "#e11d48"
            grade = "Excellent! 🎉" if pct >= 80 else "Good work! 👍" if pct >= 60 else "Keep practising 💪"
            st.markdown(
                f"""
                <div class="animate-in" style="padding:2rem;border-radius:16px;
                            background:rgba(16,185,129,0.08);border:1px solid rgba(16,185,129,0.2);
                            text-align:center;margin-top:1rem;">
                    <div style="font-size:3.5rem;font-weight:900;font-family:'Space Grotesk',sans-serif;
                                color:{color};">{score}/{len(quiz)}</div>
                    <div style="font-size:1.1rem;color:#64748b;margin-top:0.5rem;">{pct}% — {grade}</div>
                    <div style="font-size:0.8rem;color:#64748b;margin-top:0.25rem;">
                        Score saved to Progress Dashboard
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if pct == 100:
                st.balloons()


# ══════════════════════════════════════════════════════════════════════════════
#  SMART SEQUENCE  (formerly Roadmap)
# ══════════════════════════════════════════════════════════════════════════════
elif page_name == "Smart Sequence":
    page_header("🗺️", "Smart Sequence", "AI-ranked reading order for your uploaded documents — fundamentals first, advanced last.")

    summaries = [
        {"name": name, "summary": summary}
        for name, summary in st.session_state.summaries.items()
    ]
    docs_with_text = [d for d in st.session_state.documents if d["text"]]

    if len(st.session_state.documents) < 2:
        st.markdown(
            """
            <div class="glass-card animate-in" style="text-align:center;padding:3rem;">
                <div style="font-size:3rem;margin-bottom:1rem;">📚</div>
                <h3 style="margin:0 0 0.5rem;">Upload Multiple Documents First</h3>
                <p style="color:#64748b;">Smart Sequence requires at least 2 documents to generate a meaningful reading order.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    elif len(summaries) < len(docs_with_text):
        st.warning("⚠️ Generate Big Picture summaries for all files first. Smart Sequence uses those summaries to rank documents.")
        if st.button("🔍 Generate Missing Summaries", use_container_width=True):
            with st.spinner("Preparing summaries…"):
                for doc in st.session_state.documents:
                    if doc["text"] and doc["name"] not in st.session_state.summaries:
                        st.session_state.summaries[doc["name"]] = generate_short_summary(doc["name"], doc["text"])
            st.rerun()
    else:
        gen_col, _ = st.columns([1, 2])
        with gen_col:
            if st.button("🗺️ Generate Smart Sequence", use_container_width=True):
                with st.spinner("Sequencing your materials by complexity…"):
                    st.session_state.roadmap = generate_study_roadmap(summaries)

        if st.session_state.roadmap:
            st.markdown("<div class='section-label' style='margin-top:1.5rem;'>Recommended Reading Order</div>", unsafe_allow_html=True)
            st.markdown('<div class="timeline">', unsafe_allow_html=True)
            for item in st.session_state.roadmap:
                step      = item.get("step", "")
                file_name = item.get("file", "Untitled")
                reason    = item.get("reason", "")
                focus     = item.get("focus", "")
                st.markdown(
                    f"""
                    <div class="timeline-item animate-in">
                        <div class="timeline-step">{step}</div>
                        <div>
                            <h4>{file_name}</h4>
                            <p>{reason}</p>
                            <small>🎯 Focus: {focus}</small>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  TASK MANAGER
# ══════════════════════════════════════════════════════════════════════════════
elif page_name == "Task Manager":
    page_header("✅", "Task Manager", "Add study tasks, then set their priority order as your plan changes.")

    with st.form("task_form", clear_on_submit=True):
        t_col1, t_col2 = st.columns([4, 1])
        with t_col1:
            task_name = st.text_input("New study task", placeholder="e.g. Review Chapter 5 notes…")
        with t_col2:
            st.markdown("<div class='task-form-spacer'></div>", unsafe_allow_html=True)
            submitted = st.form_submit_button("➕ Add", use_container_width=True)
        if submitted and task_name.strip():
            add_task(task_name.strip())
            st.success("Task added!")

    st.markdown("<div class='section-label' style='margin-top:1.25rem;'>Active Tasks</div>", unsafe_allow_html=True)

    prod_data = normalize_task_priorities()
    active = [t for t in prod_data["tasks"] if not t["completed"]]

    def render_task_item(task: dict, position: int, total_tasks: int) -> None:
        c_name, c_priority, c_btn = st.columns([5, 1.35, 0.7])
        with c_name:
            task_name = escape(task["name"])
            st.markdown(
                f"""
                <div class="task-item">
                    <span class="task-main"><strong>{position}.</strong> {task_name}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c_priority:
            selected_priority = st.selectbox(
                "Priority",
                list(range(1, total_tasks + 1)),
                index=position - 1,
                key=f"priority_{task['id']}_{position}_{total_tasks}",
                label_visibility="collapsed",
                help="Choose this task's priority position.",
            )
            if selected_priority != position:
                update_task_priority(task["id"], selected_priority)
                st.rerun()
        with c_btn:
            if st.button("✓", key=f"done_{task['id']}", help="Mark as done"):
                complete_task(task["id"])
                st.rerun()

    active_sorted = sorted(active, key=lambda t: (t.get("priority", t.get("id", 0)), t.get("id", 0)))

    if active_sorted:
        st.markdown("<div style='margin-bottom: 1rem;'>", unsafe_allow_html=True)
        for i, t in enumerate(active_sorted):
            render_task_item(t, i + 1, len(active_sorted))
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("No active tasks! You're all caught up. 🎉")


# ══════════════════════════════════════════════════════════════════════════════
#  POMODORO TIMER  (non-blocking JS countdown)
# ══════════════════════════════════════════════════════════════════════════════
elif page_name == "Pomodoro Timer":
    page_header("⏱️", "Pomodoro Timer", "25-minute deep-focus sessions with 5-minute breaks to maximise your study efficiency.")

    # Stats row
    prod_data = load_productivity()
    sessions_done = prod_data.get("pomodoro_sessions", 0)
    s1, s2, s3 = st.columns(3)
    with s1:
        render_metric_card("🍅 Sessions Done", sessions_done, "all time")
    with s2:
        render_metric_card("⏱️ Focus Time", f"{sessions_done * 25} min", "total accumulated")
    with s3:
        render_metric_card("🎯 Sessions Today", "—", "track your streak")

    st.markdown("<hr style='border-color:rgba(99,179,237,0.1);margin:1.5rem 0;'>", unsafe_allow_html=True)

    # Pomodoro Timer Implementation
    now = time.time()
    end_time = st.session_state.pomodoro_end_time
    mode     = st.session_state.pomodoro_mode

    remaining = 0
    active = False
    if end_time is not None:
        remaining = max(0, end_time - now)
        active = remaining > 0

    mode_label  = "Focus Session 🍅" if mode == "focus" else "Break Time ☕"
    mode_color  = "#2563eb" if mode == "focus" else "#0f766e"
    duration_min = 25 if mode == "focus" else 5
    total_secs   = duration_min * 60

    st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)
    timer_placeholder = st.empty()
    st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)
    
    b1, b2, b3 = st.columns(3)

    with b1:
        if st.button("🍅 Start Focus (25 min)", use_container_width=True, disabled=active):
            st.session_state.pomodoro_end_time = time.time() + 25 * 60
            st.session_state.pomodoro_mode = "focus"
            st.rerun()

    with b2:
        if st.button("☕ Start Break (5 min)", use_container_width=True, disabled=active):
            st.session_state.pomodoro_end_time = time.time() + 5 * 60
            st.session_state.pomodoro_mode = "break"
            st.rerun()

    with b3:
        if st.button("⏹ Stop Timer", use_container_width=True, disabled=not active):
            if mode == "focus":
                log_pomodoro_session()
            st.session_state.pomodoro_end_time = None
            st.rerun()

    # The actual real-time countdown loop
    if active:
        while True:
            now = time.time()
            remaining = max(0, end_time - now)
            
            mins = int(remaining) // 60
            secs = int(remaining) % 60
            time_str = f"{mins:02d}:{secs:02d}"
            pct = 1.0 - (remaining / total_secs)

            timer_placeholder.markdown(
                f"""
                <div class="timer-display animate-in">
                    <div style="font-size:0.8rem;text-transform:uppercase;letter-spacing:0.12em;
                                color:#64748b;margin-bottom:0.5rem;">{mode_label}</div>
                    <div class="timer-digits" style="color:{mode_color};">{time_str}</div>
                    <div style="margin-top:0.75rem;font-size:0.85rem;color:#64748b;">
                        🔴 Running — stay focused!
                    </div>
                    <div style="margin-top: 1rem; width: 100%; height: 6px; background: #e2e8f0; border-radius: 4px; overflow: hidden;">
                        <div style="height: 100%; width: {pct*100}%; background: {mode_color};"></div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            
            if remaining <= 0:
                break
                
            time.sleep(1)
            
        # Session complete logic runs after loop exits
        if mode == "focus":
            st.success("🎉 Focus session complete! Great work. Log a break or start another session.")
            log_pomodoro_session()
            st.balloons()
        else:
            st.info("☕ Break is over. Ready to focus again?")
        st.session_state.pomodoro_end_time = None
    else:
        # Initial non-active state render
        timer_placeholder.markdown(
            f"""
            <div class="timer-display animate-in">
                <div style="font-size:0.8rem;text-transform:uppercase;letter-spacing:0.12em;
                            color:#64748b;margin-bottom:0.5rem;">Ready</div>
                <div class="timer-digits" style="color:#2563eb;">25:00</div>
                <div style="margin-top:0.75rem;font-size:0.85rem;color:#64748b;">
                    ⏸ Ready to start
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
#  PROGRESS DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
elif page_name == "Progress":
    page_header("📊", "Progress Dashboard", "Track your quiz scores, Pomodoro sessions, and task completion over time.")

    study_data = load_progress()
    prod_data  = load_productivity()
    completed_tasks = len([t for t in prod_data["tasks"] if t["completed"]])

    # Top metrics
    pm1, pm2, pm3, pm4 = st.columns(4)
    with pm1:
        render_metric_card("📝 Quizzes Taken", len(study_data["scores"]), "sessions recorded")
    with pm2:
        avg_score = (
            f"{sum(study_data['scores'])/len(study_data['scores']):.1f}"
            if study_data["scores"] else "—"
        )
        render_metric_card("🎯 Avg Quiz Score", avg_score, "across all attempts")
    with pm3:
        render_metric_card("🍅 Pomodoros", prod_data["pomodoro_sessions"], "focus sessions")
    with pm4:
        render_metric_card("✅ Tasks Done", completed_tasks, "tasks completed")

    st.markdown("<hr style='border-color:rgba(99,179,237,0.1);margin:1.5rem 0;'>", unsafe_allow_html=True)

    ch1, ch2 = st.columns(2, gap="medium")

    with ch1:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.markdown("**📈 Quiz Performance Over Time**")
        if study_data["scores"]:
            fig = px.line(
                x=list(range(1, len(study_data["scores"]) + 1)),
                y=study_data["scores"],
                labels={"x": "Attempt #", "y": "Score"},
                markers=True,
                color_discrete_sequence=["#2563eb"],
            )
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#334155"),
                xaxis=dict(gridcolor="rgba(100,116,139,0.16)"),
                yaxis=dict(gridcolor="rgba(100,116,139,0.16)"),
                margin=dict(l=0, r=0, t=10, b=0),
            )
            fig.update_traces(line=dict(width=2.5), marker=dict(size=8))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No quiz data yet. Take a quiz to see your performance here.")
        st.markdown("</div>", unsafe_allow_html=True)

    with ch2:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.markdown("**📊 Productivity Breakdown**")
        if prod_data["tasks"] or prod_data["pomodoro_sessions"] > 0:
            active_tasks = len([t for t in prod_data["tasks"] if not t["completed"]])
            df = pd.DataFrame({
                "Category":  ["Pomodoros", "Tasks Completed", "Tasks Pending"],
                "Count":     [prod_data["pomodoro_sessions"], completed_tasks, active_tasks],
                "Color":     ["#2563eb", "#0f766e", "#d97706"],
            })
            fig2 = px.bar(
                df,
                x="Category",
                y="Count",
                color="Category",
                color_discrete_map={
                    "Pomodoros":       "#2563eb",
                    "Tasks Completed": "#0f766e",
                    "Tasks Pending":   "#d97706",
                },
            )
            fig2.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#334155"),
                xaxis=dict(gridcolor="rgba(100,116,139,0.16)"),
                yaxis=dict(gridcolor="rgba(100,116,139,0.16)"),
                showlegend=False,
                margin=dict(l=0, r=0, t=10, b=0),
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Complete tasks and Pomodoro sessions to see your breakdown here.")
        st.markdown("</div>", unsafe_allow_html=True)

    # Quiz history table
    if study_data["scores"] and study_data.get("topics"):
        st.markdown("<div class='section-label' style='margin-top:1.5rem;'>Quiz History</div>", unsafe_allow_html=True)
        history_data = {
            "Attempt": list(range(1, len(study_data["scores"]) + 1)),
            "Topic":   study_data["topics"][: len(study_data["scores"])],
            "Score":   study_data["scores"],
        }
        history_df = pd.DataFrame(history_data)
        st.dataframe(
            history_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Attempt": st.column_config.NumberColumn("# Attempt", width="small"),
                "Topic":   st.column_config.TextColumn("Topic"),
                "Score":   st.column_config.NumberColumn("Score", width="small"),
            },
        )
