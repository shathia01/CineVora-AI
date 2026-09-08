from __future__ import annotations

import base64
import html
import json
from pathlib import Path
from typing import Any

import streamlit as st

from .config import APP_NAME, APP_TAGLINE, LEARNING_TOPICS


def inject_global_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --cv-bg: #09090b;
            --cv-panel: rgba(20,20,24,.78);
            --cv-border: rgba(255,255,255,.10);
            --cv-gold: #d9b86c;
            --cv-text: #f6f3ea;
            --cv-muted: #aaa7a0;
        }
        .stApp {
            background:
              radial-gradient(circle at 18% 0%, rgba(217,184,108,.10), transparent 35%),
              radial-gradient(circle at 100% 40%, rgba(92,57,180,.09), transparent 30%),
              linear-gradient(180deg, #08090b 0%, #0d0e12 55%, #09090b 100%);
            color: var(--cv-text);
        }
        [data-testid="stHeader"] { background: transparent; }
        [data-testid="stToolbar"] { visibility: hidden; }
        .block-container { max-width: 1240px; padding-top: 2.1rem; padding-bottom: 4rem; }
        .cv-brand { font-size: clamp(2.4rem, 5vw, 5.4rem); font-weight: 800; letter-spacing: .08em; margin: 0; line-height: .95; }
        .cv-brand span { color: var(--cv-gold); }
        .cv-kicker { text-transform: uppercase; letter-spacing: .28em; color: var(--cv-gold); font-size: .75rem; font-weight: 700; }
        .cv-sub { color: var(--cv-muted); font-size: 1.04rem; max-width: 760px; }
        .cv-card {
            background: linear-gradient(180deg, rgba(255,255,255,.045), rgba(255,255,255,.018));
            border: 1px solid var(--cv-border); border-radius: 18px; padding: 1.1rem 1.2rem;
            box-shadow: 0 18px 55px rgba(0,0,0,.20); margin-bottom: .8rem;
        }
        .cv-score { font-size: 3.6rem; font-weight: 850; line-height: 1; color: var(--cv-gold); }
        .cv-muted { color: var(--cv-muted); }
        .cv-good { color: #8ed6a7; font-weight: 700; }
        .cv-warn { color: #f0c56d; font-weight: 700; }
        .cv-bad { color: #e88b8b; font-weight: 700; }
        .cv-chip { display:inline-block; border:1px solid var(--cv-border); border-radius:999px; padding:.26rem .62rem; margin:.14rem .18rem .14rem 0; font-size:.82rem; color:#e8e4db; background:rgba(255,255,255,.03); }
        div[data-testid="stMetric"] { background: rgba(255,255,255,.035); border:1px solid var(--cv-border); border-radius:16px; padding:.75rem; }
        div[data-baseweb="tab-list"] { gap: .25rem; }
        button[data-baseweb="tab"] { border-radius: 999px; padding: .5rem .75rem; }
        div.stButton > button, div.stDownloadButton > button { border-radius: 999px; font-weight: 700; }
        .cv-hero { padding: 3.2rem 0 2rem; }
        .cv-divider { height:1px; background:linear-gradient(90deg,transparent,rgba(217,184,108,.35),transparent); margin:1.4rem 0; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_intro(audio_path: Path) -> None:
    # CSS-only overlay: automatically fades away; the app is already loaded underneath.
    st.markdown(
        """
        <style>
        @keyframes cvIntroOut {
          0%, 72% { opacity: 1; visibility: visible; }
          100% { opacity: 0; visibility: hidden; pointer-events: none; }
        }
        @keyframes cvLogoIn {
          0% { opacity:0; transform:scale(.92); letter-spacing:.55em; filter:blur(10px); }
          45% { opacity:1; transform:scale(1); filter:blur(0); }
          100% { opacity:1; letter-spacing:.18em; }
        }
        @keyframes cvLine { from { transform:scaleX(0); opacity:0; } to { transform:scaleX(1); opacity:1; } }
        @keyframes cvGrain { 0%{transform:translate(0,0)}25%{transform:translate(-2%,2%)}50%{transform:translate(2%,-1%)}75%{transform:translate(1%,2%)}100%{transform:translate(0,0)} }
        .cv-intro {
          position:fixed; inset:0; z-index:999999; display:flex; align-items:center; justify-content:center; overflow:hidden;
          background: radial-gradient(circle at 50% 42%, #181511 0%, #09090b 34%, #020203 80%);
          animation: cvIntroOut 6.1s ease forwards;
        }
        .cv-intro:before { content:""; position:absolute; inset:-30%; opacity:.12; background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 180 180' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='.5'/%3E%3C/svg%3E"); animation:cvGrain .45s steps(2) infinite; }
        .cv-intro-wrap { position:relative; z-index:2; text-align:center; padding:2rem; }
        .cv-intro-logo { color:#f5f0e4; font-size:clamp(2.8rem,8vw,7rem); font-weight:800; text-transform:uppercase; text-shadow:0 0 34px rgba(217,184,108,.14); animation:cvLogoIn 3.2s cubic-bezier(.2,.8,.2,1) forwards; }
        .cv-intro-logo b { color:#d9b86c; font-weight:800; }
        .cv-intro-line { width:min(460px,70vw); height:1px; margin:1.3rem auto; background:linear-gradient(90deg,transparent,#d9b86c,transparent); transform-origin:center; animation:cvLine 1.3s 1.1s ease both; }
        .cv-intro-tag { opacity:0; color:#bcb5a5; text-transform:uppercase; letter-spacing:.42em; font-size:.72rem; animation:cvLine 1.4s 1.7s ease forwards; }
        .cv-intro-frame { position:absolute; inset:18px; border:1px solid rgba(217,184,108,.15); pointer-events:none; }
        </style>
        <div class="cv-intro">
          <div class="cv-intro-frame"></div>
          <div class="cv-intro-wrap">
            <div class="cv-intro-logo">CINEVORA <b>AI</b></div>
            <div class="cv-intro-line"></div>
            <div class="cv-intro-tag">Screenplay Intelligence</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if audio_path.exists():
        # Autoplay is attempted. Browsers can block sound until the user interacts with the page.
        st.audio(str(audio_path), format="audio/wav", autoplay=True)
        st.markdown("<style>[data-testid='stAudio']{height:0!important;overflow:hidden!important;opacity:0!important;position:absolute!important;}</style>", unsafe_allow_html=True)


def render_brand_header() -> None:
    st.markdown(
        f"""
        <div class="cv-hero">
          <div class="cv-kicker">AI Screenplay Learning Assistant</div>
          <h1 class="cv-brand">CineVora <span>AI</span></h1>
          <p class="cv-sub">{APP_TAGLINE} Built for university students, student filmmakers, and emerging screenwriters.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def chips(values: list[str]) -> str:
    return "".join(f"<span class='cv-chip'>{html.escape(str(v))}</span>" for v in values if v)


def learn_expander(topic: str) -> None:
    item = LEARNING_TOPICS.get(topic)
    if not item:
        return
    with st.expander(f"🎓 Why? — {topic}"):
        st.markdown(f"**What it means:** {item['definition']}")
        st.markdown(f"**Simple example:** {item['example']}")
        st.markdown(f"**Common mistake:** {item['mistake']}")
        st.markdown(f"**Quick tip:** {item['tip']}")


def status_icon(status: str) -> str:
    s = (status or "").lower()
    if any(word in s for word in ["good", "clear", "balanced", "present"]):
        return "🟢"
    if any(word in s for word in ["weak", "unclear", "learning", "attention", "mostly"]):
        return "🟡"
    if any(word in s for word in ["missing", "needs improvement", "rushed", "slow"]):
        return "🔴"
    return "⚪"


def download_json(data: dict[str, Any]) -> bytes:
    return json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
