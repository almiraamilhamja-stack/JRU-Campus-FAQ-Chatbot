"""JRU Campus FAQ Chatbot: Streamlit front end.

Run with:  streamlit run app.py
"""
import html
import re
import uuid
from datetime import datetime

import streamlit as st

import chat_history
import config
import document_loader
import faq_data
import rag_pipeline
import themes
import vector_store

st.set_page_config(page_title=config.APP_NAME, page_icon="🎓", layout="wide", initial_sidebar_state="expanded")
chat_history.init_db()

FONT_URL = ("https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,wght@0,600;0,700;1,600;1,700"
            "&family=Inter:wght@400;500;600;700&display=swap")      # falls back to Georgia / system sans when offline
ICONS = {   # simple line icons (inline SVG, no external files)
    "cap": "<svg viewBox='0 0 24 24'><path d='M12 4 2 9l10 5 8-4v6h2V9L12 4Z'/><path d='M6 12.5V16c0 1.4 2.7 3 6 3s6-1.6 6-3v-3.5l-6 3-6-3Z'/></svg>",
    "book": "<svg viewBox='0 0 24 24'><path d='M12 6.5C10.5 5.4 8.3 5 6 5H3v13h3c2.3 0 4.5.4 6 1.5 1.5-1.1 3.7-1.5 6-1.5h3V5h-3c-2.3 0-4.5.4-6 1.5Z' fill='none' stroke='currentColor' stroke-width='2'/><path d='M12 6.5V19' stroke='currentColor' stroke-width='2'/></svg>",
    "users": "<svg viewBox='0 0 24 24'><circle cx='9' cy='8' r='3.2'/><circle cx='17' cy='9' r='2.6'/><path d='M2.5 19c0-3.3 2.9-5.5 6.5-5.5s6.5 2.2 6.5 5.5v.5h-13Z'/><path d='M16.5 13.6c3 0 5 1.8 5 4.6v.8H17.5c0-2-.6-3.6-1.8-4.7.2-.5.5-.7.8-.7Z'/></svg>",
    "info": "<svg viewBox='0 0 24 24'><circle cx='12' cy='12' r='9.5' fill='none' stroke='currentColor' stroke-width='2'/><rect x='11' y='10.5' width='2' height='7' rx='1'/><circle cx='12' cy='7.4' r='1.3'/></svg>",
}
FONT_SIZES = themes.FONT_SIZES


# ------------------------------------------------------------------ helpers
def load_css(font_px="16px", theme="navy_gold", landing=False, mini=False):
    """styles.css first, then the theme variables (so they win over the fallback values in styles.css)."""
    css = config.CSS_PATH.read_text(encoding="utf-8") if config.CSS_PATH.exists() else ""
    extra = landing_css() if landing else (MINI_CSS if mini else "")
    st.markdown(f"<style>@import url('{FONT_URL}');\n:root{{--base-font:{font_px};}}\n{css}\n"
                f"{themes.theme_css(theme)}\n{extra}</style>", unsafe_allow_html=True)


# icon-only sidebar (the "collapsed" mode): narrow, icons only, labels become tooltips
MINI_CSS = """
section[data-testid="stSidebar"][aria-expanded="true"] { width: 78px !important; min-width: 78px !important; }
section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] { padding-left: .4rem; padding-right: .4rem; }
section[data-testid="stSidebar"] .side-uni, section[data-testid="stSidebar"] .side-assistant > div,
section[data-testid="stSidebar"] .side-sec, section[data-testid="stSidebar"] .side-foot,
section[data-testid="stSidebar"] .side-legal, section[data-testid="stSidebar"] [class*="st-key-nav_"] button p { display: none; }
section[data-testid="stSidebar"] .side-brand, section[data-testid="stSidebar"] .side-assistant { justify-content: center; }
section[data-testid="stSidebar"] .side-brand img { width: 44px; height: 44px; }
section[data-testid="stSidebar"] [class*="st-key-nav_"] button { justify-content: center; padding: .62rem 0; gap: 0; }
section[data-testid="stSidebar"] .side-rule { margin: .5rem 0; }
"""


def guest_identity():
    """No login: each browser gets an anonymous visitor id that is kept in the URL (?g=...), so its own chat history
    survives a refresh without any account. The old demo-account data in the database is left untouched."""
    gid = st.query_params.get("g", "")
    if not re.fullmatch(r"[0-9a-f]{12}", str(gid)):
        gid = uuid.uuid4().hex[:12]
        st.query_params["g"] = gid
    return {"id": f"guest-{gid}", "name": "Visitor", "role": "Guest"}


def init_state():
    defaults = {"entered": False, "conv_id": None, "pending_question": None, "confirm_delete": None,
                "page": config.DEFAULT_PAGE}
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)
    st.session_state.setdefault("user", guest_identity())


def goto(page):
    """Switch page from inside a page (the sidebar is drawn before the page, so it picks the change up on the rerun)."""
    st.session_state["page"] = page
    st.rerun()


def pref(uid, key, default):
    return chat_history.get_preference(uid, key, default)


def status_chips():
    """Both chips are computed from live state: the model loader and the ChromaDB manifest."""
    idx = vector_store.index_status()
    idx_txt = {"ready": f"Index ready ({idx['chunks']} chunks)", "stale": "Index needs rebuilding",
               "missing": "Index not built yet", "no_documents": "No documents"}[idx["state"]]
    ls = rag_pipeline.loader_status()
    model_txt, dot = {"ready": ("Chatbot online", "dot-on"), "loading": ("Starting up...", "dot-wait"),
                      "error": ("Model failed to load", "dot-off"), "idle": ("Models not started", "dot-wait")}[ls["state"]]
    idx_dot = "dot-on" if idx["state"] == "ready" else "dot-wait"
    return (f"<span class='pill'><i class='dot {dot}'></i>{model_txt}</span>"
            f"<span class='pill'><i class='dot {idx_dot}'></i>{idx_txt}</span>")


def status_view():
    """Status chips that refresh themselves every 2 seconds until the models are ready."""
    def body():
        st.markdown(status_chips(), unsafe_allow_html=True)
    ready = rag_pipeline.loader_status()["state"] in ("ready", "error")
    st.fragment(body, run_every=None if ready else 2)()


def load_banner():
    """Shown on the chat page while the models load or after they failed. Never blocks the page."""
    def body():
        ls = rag_pipeline.loader_status()
        if ls["state"] == "loading":
            st.info(f"Starting the chatbot ({int(ls['elapsed'] or 0)} s): {ls['message']}  \n"
                    "You can already type a question; it will be answered as soon as the models are ready. "
                    "The very first start downloads about 3 GB and can take several minutes.")
        elif ls["state"] == "error":
            st.error(f"The chatbot could not start. {ls['error']}")
            if st.button("Retry loading the models", key="retry_load"):
                rag_pipeline.start_loading(force=True)
                st.rerun()
    ls0 = rag_pipeline.loader_status()["state"]
    st.fragment(body, run_every=1 if ls0 == "loading" else None)()


def logo_html(size=64):
    """The supplied seal (served from static/); a plain text monogram only if the file is missing."""
    url = config.static_url("jru_logo.png")
    if url:
        return f"<img src='{url}' width='{size}' height='{size}' alt='JRU seal'>"
    return "<span class='monogram'>JRU</span>"


def landing_css():
    """Landing page only. Left half: navy panel with the campus photo; a curved gold line divides it from the ivory right half.
    The shapes are SVG masks, so they scale with the window. On phones the panel becomes a banner with a curved bottom edge."""
    url = config.static_url("jru_campus_login.jpg")
    photo = (f"linear-gradient(180deg, #0B1F38 0%, rgba(11,31,56,.88) 20%, rgba(11,31,56,.4) 38%, rgba(11,31,56,0) 56%), "
             f"url('{url}') 14% 100%/cover no-repeat, #0B1F38") if url else "linear-gradient(160deg, #102B4E, #0B1F38)"
    side = ("url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100' preserveAspectRatio='none'%3E"
            "%3Cpath d='M0 0H{x}C{a} 22 {b} 42 {c} 62C{d} 76 {e} 90 {f} 100H0Z'/%3E%3C/svg%3E\") 0 0/100% 100% no-repeat")
    bot = ("url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100' preserveAspectRatio='none'%3E"
           "%3Cpath d='M0 0H100V{r}C70 100 30 {m} 0 {l}Z'/%3E%3C/svg%3E\") 0 0/100% 100% no-repeat")
    bottom, bottom_gold = bot.format(r=86, m=80, l=96), bot.format(r=90, m=84, l=99)
    wide = side.format(x=88, a=96, b=84, c=90, d=93, e=88, f=80)
    wide_gold = side.format(x=89.8, a=97.8, b=85.8, c=91.8, d=94.8, e=89.8, f=81.8)
    return (".stApp { background: #F8F6F0; }\n"
            ".stApp::before, .stApp::after { content:''; position:fixed; left:0; top:0; bottom:0; pointer-events:none; }\n"
            f".stApp::after {{ width:56%; z-index:0; background:#D4A843; -webkit-mask:{wide_gold}; mask:{wide_gold}; }}\n"
            f".stApp::before {{ width:55%; z-index:1; background:{photo}; -webkit-mask:{wide}; mask:{wide}; }}\n"
            ".block-container { max-width:100% !important; padding:0 !important; position:relative; z-index:2; }\n"
            "[data-testid='stSidebar'], [data-testid='stSidebarCollapsedControl'] { display:none; }\n"
            "@media (max-width: 900px) {\n"
            "  .stApp::before, .stApp::after { width:100%; height:46vh; bottom:auto; }\n"
            "  .stApp::after { height:calc(46vh + 10px); }\n"
            f"  .stApp::before {{ -webkit-mask:{bottom}; mask:{bottom}; }}\n"
            f"  .stApp::after {{ -webkit-mask:{bottom_gold}; mask:{bottom_gold}; }}\n"
            "}\n")


def page_header(user):
    left, right = st.columns([5, 1.4])
    left.markdown(f"<div class='top-bar'>{logo_html(52)}<span class='top-sep'></span><div>"
                  f"<div class='top-title'>{config.APP_NAME}</div>"
                  f"<div class='top-sub'>{config.APP_TAGLINE}</div></div></div>", unsafe_allow_html=True)
    with right.container(key="home_link"):
        if st.button("← Welcome page", key="to_landing", use_container_width=True):
            leave()


def stamp(iso):
    try:
        return datetime.fromisoformat(iso).astimezone().strftime("%I:%M %p").lstrip("0")
    except Exception:
        return ""


# ------------------------------------------------------------------ landing page
CHAT_ICON = ("<svg viewBox='0 0 64 56' width='72' height='64' aria-hidden='true'><path d='M8 6h32a6 6 0 0 1 6 6v18a6 6 0 0 1-6 6H22l-9 8v-8H8a6 6 0 0 1-6-6V12a6 6 0 0 1 6-6Z' "
             "fill='none' stroke='#0B1F38' stroke-width='4' stroke-linejoin='round'/><circle cx='15' cy='21' r='2.6' fill='#0B1F38'/>"
             "<circle cx='25' cy='21' r='2.6' fill='#0B1F38'/><circle cx='35' cy='21' r='2.6' fill='#0B1F38'/>"
             "<path d='M50 20h2a8 8 0 0 1 8 8v10a8 8 0 0 1-8 8h-2v7l-8-7H33' fill='none' stroke='#D4A843' stroke-width='4' stroke-linejoin='round' stroke-linecap='round'/></svg>")


def enter_app():
    st.session_state["entered"] = True
    st.session_state["page"] = config.DEFAULT_PAGE


def landing_page():
    left, right = st.columns(2, gap="small")
    with left:
        st.markdown(f"<div class='lp-left'><div class='lp-brand'>{logo_html(112)}<span class='lp-sep'></span><div>"
                    "<div class='lp-uni'>JOSE RIZAL<br>UNIVERSITY</div>"
                    f"<div class='lp-slogan'>{html.escape(config.SIDEBAR_TAGLINE)}</div></div></div></div>", unsafe_allow_html=True)
    with right:
        with st.container(key="lp_right"):
            st.markdown(f"<div class='lp-icon'>{CHAT_ICON}</div><h1 class='lp-title'>{config.APP_NAME}</h1>"
                        "<div class='lp-rule'></div>"
                        f"<div class='lp-sub'>{config.APP_TAGLINE}</div>"
                        "<p class='lp-desc'>Ask me about admissions, enrollment, library, student services, and more "
                        "from the JRU handbooks.</p>", unsafe_allow_html=True)
            with st.container(key="get_started"):
                if st.button("Get Started", key="btn_start", type="primary"):
                    enter_app()
                    st.rerun()


# ------------------------------------------------------------------ sidebar
def nav_to(slug):
    st.session_state["page"] = slug


def toggle_mini(uid):
    mini = not st.session_state.get("nav_mini", False)
    st.session_state["nav_mini"] = mini
    chat_history.set_preference(uid, "nav_mini", "1" if mini else "0")


def sidebar(user):
    """Branding, the sectioned menu (every entry is a real page, see config.NAV) and a collapse-to-icons toggle."""
    mini = st.session_state.get("nav_mini", False)
    current = st.session_state.get("page", config.DEFAULT_PAGE)
    with st.sidebar:
        st.markdown(f"<div class='side-brand'>{logo_html(56)}<div class='side-uni'>JOSE RIZAL<br>UNIVERSITY</div></div>"
                    "<div class='side-rule'></div>"
                    f"<div class='side-assistant'><span class='bot-ico'></span><div>{config.SYSTEM_NAME}</div></div>",
                    unsafe_allow_html=True)
        with st.container(key="sbtoggle"):
            st.button("»" if mini else "« Collapse menu", key="btn_mini", on_click=toggle_mini, args=(user["id"],),
                      help="Show labels" if mini else "Show icons only", use_container_width=True)
        for section, items in config.NAV:
            st.markdown(f"<div class='side-sec'>{section}</div>" if not mini else "<div class='side-rule'></div>",
                        unsafe_allow_html=True)
            for slug, label in items:
                with st.container(key=f"nav_{slug}"):
                    st.button(label, key=f"navbtn_{slug}", on_click=nav_to, args=(slug,), help=label,
                              type="primary" if slug == current else "secondary", use_container_width=True)
        st.markdown("<div class='side-rule'></div><div class='side-foot'><span class='side-jru'>JRU</span> – "
                    + html.escape(config.SIDEBAR_TAGLINE) + "</div>"
                    f"<div class='side-legal'>{html.escape(config.DISCLAIMER)}</div>", unsafe_allow_html=True)


def leave():
    """Back to the landing page. The visitor id (and therefore the saved history) is kept."""
    for k in ("conv_id", "pending_question", "confirm_delete", "page", "cat_sel", "job"):
        st.session_state.pop(k, None)
    st.session_state["entered"] = False
    st.rerun()


# ------------------------------------------------------------------ chatbot
def render_sources(sources, expanded):
    if not sources:
        return
    for s in sources:
        page = f"page {s['page']}" if s.get("page") else "page not available"
        pdf = f" (PDF page {s['pdf_page']})" if s.get("pdf_page") else ""
        st.markdown(f"<div class='source-card'>📄 <b>{html.escape(str(s['handbook']))}</b>, {page}{pdf}<br>"
                    f"<small>Source: {html.escape(str(s['document']))}</small></div>", unsafe_allow_html=True)
    with st.expander("Show the retrieved passages", expanded=expanded):
        for s in sources:
            st.caption(f"{s['handbook']}, page {s.get('page')}: {s.get('snippet', '')}")


def render_timings(t):
    if not t:
        return
    parts = [("Query embedding", t.get("embed")), ("Retrieval", t.get("search")), ("Generation", t.get("generation")),
             ("Saved answer lookup", t.get("cache")), ("Total", t.get("total"))]
    st.caption("Timing: " + " · ".join(f"{n} {v:.2f} s" for n, v in parts if v is not None))


def render_message(m, expanded):
    when = stamp(m.get("created_at", ""))
    if m["role"] == "user":
        st.markdown(f"<div class='row-right'><div class='bubble-user'>{html.escape(m['content'])}</div>"
                    f"<div class='stamp'>{when}</div></div>", unsafe_allow_html=True)
    else:
        with st.chat_message("assistant", avatar="🎓"):
            st.markdown(m["content"])
            render_sources(m.get("sources"), expanded)
            with st.expander("Copy answer"):
                st.code(m["content"], language=None)
            if when:
                st.markdown(f"<div class='stamp'>{when}</div>", unsafe_allow_html=True)


def submit_question(uid, question):
    """Store the question and start the background answer job. Ignored while another answer is still running."""
    job = st.session_state.get("job")
    if job is not None and not job.done:
        st.warning("Please wait: the previous question is still being answered.")
        return
    if st.session_state["conv_id"] is None:
        st.session_state["conv_id"] = chat_history.create_conversation(uid, question[:60])
    conv_id = st.session_state["conv_id"]
    history = chat_history.get_messages(uid, conv_id)
    chat_history.add_message(uid, conv_id, "user", question)
    st.session_state["job"] = rag_pipeline.AnswerJob(question, history)
    st.session_state["job_conv"] = conv_id
    st.session_state["page"] = "chat"      # a question asked from any page is answered in the Chat Assistant
    st.rerun()


def job_view(uid, expand_sources):
    """Shows the running answer (live text, status, Stop button) and saves it when finished. Polls every 0.4 s."""
    def body():
        job = st.session_state.get("job")
        if job is None:
            return
        if not job.done:
            ls = rag_pipeline.loader_status()
            with st.chat_message("assistant", avatar="🎓"):
                if job.stage == "waiting_models":
                    st.markdown(f"⏳ **Starting the chatbot** ({int(ls['elapsed'] or 0)} s). {ls['message']}")
                    st.caption("Models load once per server start; later questions are much faster.")
                elif job.stage == "queued":
                    st.markdown("⏳ Waiting for another answer to finish...")
                elif job.stage == "searching":
                    st.markdown("🔎 Searching the handbooks...")
                else:
                    st.markdown((job.text or "✍️ Writing the answer...") + " ▌")
                if st.button("Stop", key="stop_job"):
                    job.cancel.set()
            return
        if not job.saved:
            job.saved = True
            conv_id = st.session_state.get("job_conv")
            if job.stage == "error":
                answer, sources = f"Sorry, I could not answer this question. {job.error}", []
            else:
                answer, sources = job.result["answer"], job.result["sources"]
                if job.result.get("stopped") and job.text and answer == "Stopped.":
                    answer = job.text
            try:
                chat_history.add_message(uid, conv_id, "assistant", answer, sources)
            except Exception:
                pass
            st.session_state["last_timings"] = (job.result or {}).get("timings")
            st.session_state["job"] = None
            st.rerun(scope="app")

    job = st.session_state.get("job")
    st.fragment(body, run_every=0.4 if (job is not None and not job.done) else None)()


def composer(uid):
    """The question box, shared by Overview and Chat Assistant. A question from a suggestion button arrives as
    pending_question and goes through exactly the same path as typed text."""
    typed = st.chat_input("Type your question here...", max_chars=config.MAX_QUESTION_CHARS)
    question = typed or st.session_state.pop("pending_question", None)
    if not question:
        return
    question = question.strip()
    if not question:
        st.warning("Please type a question.")
        return
    submit_question(uid, question)


def section_head(icon, title, sub=""):
    sub_html = f"<div class='sec-sub'>{sub}</div>" if sub else ""
    st.markdown(f"<div class='sec-head'><span class='sec-ico'>{icon}</span><div><div class='sec-title'>{title}</div>"
                f"{sub_html}</div></div>", unsafe_allow_html=True)


def category_cards(on_pick):
    """The four category cards. Each card is an invisible button laid over it; on_pick(i) runs when one is clicked."""
    with st.container(key="catgrid"):
        cols = st.columns(len(config.HOME_CARDS))
        for i, (label, icon, _cats, desc) in enumerate(config.HOME_CARDS):
            with cols[i].container(key=f"card_{i}"):
                st.markdown(f"<div class='cat-card'><div class='cat-top'><div class='cat-icon'>{ICONS[icon]}</div>"
                            f"<div class='cat-title'>{html.escape(label)}</div></div><div class='cat-rule'></div>"
                            f"<div class='cat-desc'>{html.escape(desc)}</div><div class='cat-go'>→</div></div>",
                            unsafe_allow_html=True)
                if st.button(f"Open {label}", key=f"cat_{i}", use_container_width=True):
                    on_pick(i)


# ------------------------------------------------------------------ Overview
def overview_page(user):
    uid = user["id"]
    hero_img = config.static_url("jru_campus_hero.jpg")
    img = f"<div class='hero-img' style=\"background-image:url('{hero_img}')\"></div>" if hero_img else ""
    st.markdown("<div class='hero-banner'><div class='hero-gold'></div>" + img +
                "<div class='hero-text'><div class='hero-bar'></div>"
                "<div class='hero-hi'>Good day!</div><div class='hero-underline'></div>"
                "<div class='hero-sub'>I'm your JRU Campus FAQ Chatbot.</div>"
                "<div class='hero-note'>Ask me about admissions, enrollment, library, student services, "
                "and more from the JRU handbooks.</div></div></div>", unsafe_allow_html=True)
    load_banner()
    section_head("▦", "Explore Campus Information", "Choose a category or ask the chatbot directly.")

    def pick(i):
        st.session_state["cat_sel"] = i
        goto("campus")
    category_cards(pick)
    section_head("💬", "Popular Questions")
    with st.container(key="chips"):
        ccols = st.columns(len(config.POPULAR_QUESTIONS))
        for i, q in enumerate(config.POPULAR_QUESTIONS):
            if ccols[i].button(q, key=f"pop_{i}", use_container_width=True):
                st.session_state["pending_question"] = q
    composer(uid)


# ------------------------------------------------------------------ Chat Assistant
def chat_page(user):
    uid = user["id"]
    expand_sources = pref(uid, "expand_sources", "0") == "1"
    messages = chat_history.get_messages(uid, st.session_state["conv_id"]) if st.session_state["conv_id"] else []
    busy = st.session_state.get("job") is not None
    load_banner()
    c1, c2, _ = st.columns([1, 1.4, 5])
    if c1.button("➕ New Chat", use_container_width=True, disabled=busy):
        st.session_state["conv_id"] = None
        st.rerun()
    if c2.button("🧹 Clear Conversation", use_container_width=True, disabled=busy or not messages):
        chat_history.clear_conversation(uid, st.session_state["conv_id"])
        st.rerun()
    if not messages and not busy:
        st.markdown("<div class='empty-state'>Ask a question about the JRU handbooks below, or pick one from "
                    "<b>Overview</b>, <b>Frequently Asked Questions</b> or <b>Campus Information</b>.</div>", unsafe_allow_html=True)
    for m in messages:
        render_message(m, expand_sources)
    if busy:
        job_view(uid, expand_sources)
    elif messages and st.session_state.get("last_timings"):
        render_timings(st.session_state["last_timings"])
    composer(uid)


# ------------------------------------------------------------------ Campus Information
def campus_page(user):
    st.markdown("<h2 class='page-title'>Campus Information</h2>", unsafe_allow_html=True)
    st.caption("Browse by topic. Each suggested question was checked against the handbooks and opens in the Chat Assistant.")

    def pick(i):
        st.session_state["cat_sel"] = None if st.session_state.get("cat_sel") == i else i
        st.rerun()
    category_cards(pick)
    sel = st.session_state.get("cat_sel")
    if sel is None:
        st.markdown("<div class='empty-state'>Choose a category above to see suggested questions.</div>", unsafe_allow_html=True)
        return
    label, _icon, cats, desc = config.HOME_CARDS[sel]
    st.markdown(f"<div class='cat-intro'><b>{html.escape(label)}</b><br>{html.escape(desc)}</div>", unsafe_allow_html=True)
    by_cat = faq_data.faqs_by_category(config.CATEGORIES)
    items = [f for c in cats for f in by_cat.get(c, [])]
    if not items:
        st.caption("No verified question for this category in the supplied handbooks (for example, library opening "
                   "hours are not in them). You can still type your own question in the Chat Assistant.")
    for f in items:
        if st.button(f["question"], key=f"sugg_{f['id']}"):
            st.session_state["pending_question"] = f["question"]
            goto("chat")


# ------------------------------------------------------------------ FAQ
def faq_page(user):
    st.markdown("<h2 class='page-title'>Frequently Asked Questions</h2>", unsafe_allow_html=True)
    st.caption("Every answer below comes from the supplied handbooks and shows the page it was verified on.")
    c_search, c_filter = st.columns([3, 1.4])
    q = c_search.text_input("Search the FAQ", placeholder="Search for a word such as 'leave', 'enrolment' or 'ID'",
                            label_visibility="collapsed").strip().lower()
    chosen = c_filter.selectbox("Category", ["All categories"] + config.CATEGORIES, label_visibility="collapsed")
    by_cat = faq_data.faqs_by_category(config.CATEGORIES)
    shown = 0
    for cat in (config.CATEGORIES if chosen == "All categories" else [chosen]):
        items = [f for f in by_cat[cat] if not q or q in f["question"].lower() or q in f["answer"].lower()]
        shown += len(items)
        if q and not items:
            continue
        with st.expander(f"{cat} ({len(items)})", expanded=bool(q) and bool(items)):
            if not items:
                st.caption("No verified question for this category in the supplied handbooks.")
            for f in items:
                st.markdown(f"**{f['question']}**")
                st.write(f["answer"])
                st.caption(f"Source: {f['handbook']}, page {f['page']}")
                if st.button("Ask this in the chatbot", key=f"faq_ask_{f['id']}"):
                    st.session_state["pending_question"] = f["question"]
                    goto("chat")
                st.divider()
    if q and shown == 0:
        st.markdown("<div class='empty-state'>No FAQ matches your search. Try another word, or ask the chatbot directly.</div>",
                    unsafe_allow_html=True)


# ------------------------------------------------------------------ reference documents
def documents_page(user):
    st.markdown("<h2 class='page-title'>Documents</h2><div class='top-sub'>Source materials used by the chatbot (RAG).</div>", unsafe_allow_html=True)
    idx = vector_store.index_status()
    status_label = {"ready": "Indexed", "stale": "Needs re-indexing", "missing": "Not indexed yet",
                    "no_documents": "No documents"}[idx["state"]]
    st.markdown(status_chips(), unsafe_allow_html=True)
    docs = document_loader.describe_documents()
    if not docs:
        st.markdown("<div class='empty-state'>No reference documents found in the data folder.</div>", unsafe_allow_html=True)
    for d in docs:
        card, btn = st.columns([6, 1.3])
        card.markdown(
            f"<div class='jru-card doc-row'><span class='pdf-badge'>PDF</span><div><b>{html.escape(d['title'])}</b><br>"
            f"<small>{d['pages'] or '?'} pages · {d['size_mb']} MB · file date {d['modified']}</small>"
            f"<div class='doc-desc'>{html.escape(d['description'])}</div>"
            f"<span class='chip chip-on'>Status: {status_label}</span></div></div>", unsafe_allow_html=True)
        try:
            data = (config.DATA_DIR / d["file"]).read_bytes()
            btn.download_button("Download →", data, file_name=d["file"], mime="application/pdf", key=f"dl_{d['file']}",
                                help="Downloads the PDF so you can open it")
        except OSError:
            btn.caption("File unreadable")
    if idx["built_at"]:
        st.caption(f"Index built {idx['built_at']} with chunk size {config.CHUNK_SIZE}, overlap {config.CHUNK_OVERLAP}.")


# ------------------------------------------------------------------ chat history
def history_page(user):
    uid = user["id"]
    st.markdown("<h2 class='page-title'>Conversation History</h2>", unsafe_allow_html=True)
    if st.button("➕ Start a new conversation"):
        st.session_state["conv_id"] = None
        goto("chat")
    convs = chat_history.list_conversations(uid)
    term = st.text_input("Search conversations", placeholder="Search your conversations by title",
                         label_visibility="collapsed").strip().lower()
    if term:
        convs = [c for c in convs if term in c["title"].lower()]
    if not convs:
        st.markdown("<div class='empty-state'>You have no saved conversations yet.</div>", unsafe_allow_html=True)
        return
    for c in convs:
        with st.container(border=True):
            a, b, d = st.columns([5, 1.2, 1.2])
            a.markdown(f"**{c['title']}**  \n<small>{c['n_messages']} messages · last activity {c['updated_at'].replace('T', ' ')} UTC</small>",
                       unsafe_allow_html=True)
            if b.button("Open", key=f"open_{c['id']}"):
                st.session_state["conv_id"] = c["id"]
                goto("chat")
            if d.button("Delete", key=f"del_{c['id']}"):
                st.session_state["confirm_delete"] = c["id"]
                st.rerun()
            if st.session_state["confirm_delete"] == c["id"]:
                st.warning("Delete this conversation? This cannot be undone.")
                y, n, _ = st.columns([1, 1, 4])
                if y.button("Yes, delete", key=f"yes_{c['id']}"):
                    chat_history.delete_conversation(uid, c["id"])
                    if st.session_state["conv_id"] == c["id"]:
                        st.session_state["conv_id"] = None
                    st.session_state["confirm_delete"] = None
                    st.rerun()
                if n.button("Cancel", key=f"no_{c['id']}"):
                    st.session_state["confirm_delete"] = None
                    st.rerun()


# ------------------------------------------------------------------ Knowledge Base

def kb_page(user):
    st.markdown(
        "<h2 class='page-title'>Knowledge Base</h2>"
        "<div class='top-sub'>How the chatbot finds and writes its answers.</div>",
        unsafe_allow_html=True
    )
    st.markdown(status_chips(), unsafe_allow_html=True)

    idx = vector_store.index_status()
    info = None

    # Answer caching is currently disabled.
    cache = {
        "enabled": False,
        "size": 0,
        "capacity": 0,
        "hits": 0
    }

    tiles = [
        ("Language model", config.LLM_MODEL),
        ("Embedding model", config.EMBEDDING_MODEL),
        ("Vector database", f"ChromaDB · {config.COLLECTION_NAME}"),
        ("Chunking", f"{config.CHUNK_SIZE} characters, overlap {config.CHUNK_OVERLAP}"),
        ("Retrieved chunks (top-k)",
         str(info["top_k"]) if info else
         f"{config.TOP_K_GPU} on a GPU, {config.TOP_K_CPU} on a CPU"),
        ("Running on",
         f"{info['device']} ({info['dtype']})" if info else "not loaded yet"),
        ("Model start-up time",
         f"{info['load_times'].get('total', 0):.0f} s (once per server start)"
         if info else "not loaded yet"),
        ("Index status", f"{idx['state']} ({idx['chunks']} chunks)"),
        ("Saved answers", "Disabled")
    ]

    st.markdown(
        "<div class='kb-grid'>" +
        "".join(
            f"<div class='kb-item'><small>{html.escape(k)}</small>"
            f"<b>{html.escape(v)}</b></div>"
            for k, v in tiles
        ) +
        "</div>",
        unsafe_allow_html=True
    )

    st.caption(config.DISCLAIMER)
    st.markdown("### Manage the index")

    if not config.ADMIN_MODE:
        st.caption(
            "Index maintenance is available to the person who runs this server "
            "(start it with JRU_ADMIN=1)."
        )
        return

    if st.button(
        "🔄 Rebuild the vector index",
        help="Re-reads the PDFs and rebuilds ChromaDB. Slow on a CPU."
    ):
        with st.status("Rebuilding the index...", expanded=True) as status:
            try:
                result = vector_store.rebuild_index(progress=status.write)
                status.update(
                    label=f"Index rebuilt: {result['chunks']} chunks",
                    state="complete"
                )
                for p in result["problems"]:
                    st.warning(p)
            except Exception as exc:
                status.update(label="Rebuild failed", state="error")
                st.error(f"{type(exc).__name__}: {exc}")

    up = st.file_uploader("Add a PDF reference document", type=["pdf"])

    if up is not None and st.button("Validate and save the uploaded PDF"):
        ok, msg, safe = document_loader.validate_upload(
            up.name, up.getvalue()
        )
        if ok:
            (config.DATA_DIR / safe).write_bytes(up.getvalue())
            st.success(
                f"Saved as {safe}. Use 'Rebuild the vector index' "
                "so the chatbot can use it."
            )
        else:
            st.error(msg)



# ------------------------------------------------------------------ Settings

def settings_page(user):
    uid = user["id"]

    st.markdown("<h2 class='page-title'>Settings</h2>", unsafe_allow_html=True)
    st.markdown("### Answers")

    def save_expand():
        chat_history.set_preference(
            uid,
            "expand_sources",
            "1" if st.session_state["set_expand"] else "0"
        )

    st.checkbox(
        "Show the retrieved passages expanded under every answer",
        value=pref(uid, "expand_sources", "0") == "1",
        key="set_expand",
        on_change=save_expand
    )

    st.caption(
        "Answer caching is currently disabled. "
        "Each question is processed through the RAG pipeline."
    )

    st.markdown("### Look and feel")
    st.caption("Colour theme and text size are on the Appearance page.")

    if st.button("Open Appearance", key="to_appearance"):
        goto("appearance")

    st.markdown("### Session")
    st.caption(
        "Your conversations are saved for this browser. "
        "Keep the page address (it ends with ?g=...) to see them again."
    )

    if st.button("Return to the welcome page", key="settings_home"):
        leave()



# ------------------------------------------------------------------ Appearance
def theme_card_html(key, selected):
    t = themes.THEMES[key]
    bars = "".join(f"<i style='background:{t['sb_text']}'></i>" for _ in range(4))
    return (f"<div class='theme-card{' sel' if selected else ''}'><div class='theme-prev'>"
            f"<div class='tp-side' style='background:linear-gradient(180deg,{t['sb1']},{t['sb2']})'>{bars}</div>"
            f"<div class='tp-main' style='background:{t['page']}'>"
            f"<i style='width:60%;background:{t['heading']}'></i>"
            f"<i style='width:90%;background:{t['card']};border:1px solid {t['border']}'></i>"
            f"<i class='tp-bub' style='background:{t['brand']}'></i>"
            f"<i class='tp-btn' style='background:{t['accent']}'></i></div></div>"
            f"<div class='theme-name'>{html.escape(t['name'])}</div><div class='theme-desc'>{html.escape(t['desc'])}</div></div>")


def set_theme(uid, key):
    chat_history.set_preference(uid, "theme", key)


def set_font(uid):
    chat_history.set_preference(uid, "font_size", st.session_state["font_choice"])


def appearance_page(user):
    uid = user["id"]
    current = pref(uid, "theme", themes.DEFAULT_THEME)
    if current not in themes.THEMES:
        current = themes.DEFAULT_THEME
    st.markdown("<h2 class='page-title'>Appearance</h2>", unsafe_allow_html=True)
    st.caption("Your choice is saved for this browser and applies to every page.")
    st.markdown("### Theme")
    keys = list(themes.THEMES)
    for row in (keys[:3], keys[3:]):
        cols = st.columns(3)
        for col, key in zip(cols, row):
            with col:
                st.markdown(theme_card_html(key, key == current), unsafe_allow_html=True)
                st.button("Selected ✓" if key == current else "Use this theme", key=f"theme_{key}", on_click=set_theme,
                          args=(uid, key), type="primary" if key == current else "secondary", use_container_width=True,
                          disabled=key == current)
    st.markdown("### Text size")
    size = pref(uid, "font_size", "Medium")
    if size not in FONT_SIZES:
        size = "Medium"
    st.radio("Text size", list(FONT_SIZES), index=list(FONT_SIZES).index(size), horizontal=True, key="font_choice",
             on_change=set_font, args=(uid,), label_visibility="collapsed")
    st.markdown("<div class='jru-card'><b>Preview</b><br>Admission requirements, enrollment steps and library hours are "
                "answered from the JRU handbooks, with the source page shown under each answer.</div>", unsafe_allow_html=True)


# ------------------------------------------------------------------ main
PAGE_FUNCS = {"overview": overview_page, "chat": chat_page, "faq": faq_page, "campus": campus_page,
              "documents": documents_page, "kb": kb_page, "history": history_page,
              "settings": settings_page, "appearance": appearance_page}


def main():
    init_state()
    rag_pipeline.start_loading()          # background thread; idempotent. Starts on the landing page so the models are ready sooner.
    if not st.session_state["entered"]:
        load_css(theme="navy_gold", landing=True)       # the welcome page always uses the JRU palette
        landing_page()
        return
    user = st.session_state["user"]
    uid = user["id"]
    if "nav_mini" not in st.session_state:
        st.session_state["nav_mini"] = pref(uid, "nav_mini", "0") == "1"
    theme = pref(uid, "theme", themes.DEFAULT_THEME)
    font = FONT_SIZES.get(pref(uid, "font_size", "Medium"), FONT_SIZES["Medium"])
    load_css(font, theme, mini=st.session_state["nav_mini"])
    page = st.session_state.get("page", config.DEFAULT_PAGE)
    if page not in PAGE_FUNCS:
        page = st.session_state["page"] = config.DEFAULT_PAGE
    sidebar(user)
    page_header(user)
    PAGE_FUNCS[page](user)


main()
