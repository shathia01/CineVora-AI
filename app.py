from __future__ import annotations

import os
import hashlib
from pathlib import Path

import streamlit as st

from src.ai_engine import analyse_script
from src.config import APP_NAME, DEFAULT_MODEL, LANGUAGES, LEARNING_TOPICS, SCRIPT_TYPES
from src.parser import parse_uploaded_file, read_sample
from src.report import build_pdf_report
from src.ui import chips, download_json, inject_global_css, learn_expander, render_brand_header, render_intro, status_icon

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
SAMPLES = ROOT / "samples"

st.set_page_config(page_title="CineVora AI", page_icon="🎬", layout="wide", initial_sidebar_state="collapsed")
inject_global_css()


def get_setting(name: str, default: str = "") -> str:
    try:
        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        pass
    return os.getenv(name, default)


if "intro_shown" not in st.session_state:
    render_intro(ASSETS / "cinematic_intro.wav")
    st.session_state.intro_shown = True

if "analysis" not in st.session_state:
    st.session_state.analysis = None
if "script_text" not in st.session_state:
    st.session_state.script_text = ""
if "source_name" not in st.session_state:
    st.session_state.source_name = ""
if "source_pages" not in st.session_state:
    st.session_state.source_pages = None

render_brand_header()

def set_script(text: str, name: str, pages=None) -> None:
    clean = (text or "").strip()
    new_hash = hashlib.sha256(clean.encode("utf-8", errors="ignore")).hexdigest() if clean else ""
    old_hash = st.session_state.get("script_hash", "")
    st.session_state.script_text = clean
    st.session_state.source_name = name
    st.session_state.source_pages = pages
    st.session_state.script_hash = new_hash
    if new_hash != old_hash:
        st.session_state.analysis = None


nav = st.radio("Navigation", ["Home", "Analyse", "Learn", "About"], horizontal=True, label_visibility="collapsed")
st.markdown("<div class='cv-divider'></div>", unsafe_allow_html=True)


def home_page():
    left, right = st.columns([1.2, .8], gap="large")
    with left:
        st.markdown("### Understand → Analyse → Learn → Improve")
        st.write("CineVora AI gives screenplay feedback without taking over the student's creative decisions. It separates storytelling quality from screenplay formatting so beginners are taught rather than punished.")
        st.markdown("""
        <div class='cv-card'><b>Story Intelligence</b><br><span class='cv-muted'>Overview, genre, adaptive structure, characters, scenes, pacing, dialogue, originality and show-vs-tell.</span></div>
        <div class='cv-card'><b>Student Learning Mode</b><br><span class='cv-muted'>Short “Why?” explanations for screenplay concepts with examples and quick tips.</span></div>
        <div class='cv-card'><b>Actionable Feedback</b><br><span class='cv-muted'>Problem → Why → How to improve, followed by three prioritised next steps.</span></div>
        """, unsafe_allow_html=True)
    with right:
        st.markdown("### What CineVora checks")
        for text in [
            "Script Type + Overview", "Story / Series Structure", "Character Development", "Dialogue", "Important Scenes", "Pacing", "Originality", "Show vs Tell", "Screenplay Format", "Strengths & Weaknesses", "Overall Creative Score", "Final Feedback + Next Steps"
        ]:
            st.markdown(f"✓ {text}")
        st.info("Screenplay Format is separate from the Overall Script Score. A beginner can have a strong story even while learning professional formatting.")


def analyse_page():
    st.markdown("## Analyse a screenplay")
    st.caption("Upload PDF/DOCX/TXT, paste screenplay text, or try one of the included samples.")

    input_tab, paste_tab, sample_tab = st.tabs(["Upload", "Paste Script", "Try Sample"])

    with input_tab:
        uploaded = st.file_uploader("Upload your screenplay", type=["pdf", "docx", "txt"], help="For scanned/image-only PDFs, text extraction may be limited.")
        if uploaded is not None:
            try:
                parsed = parse_uploaded_file(uploaded)
                set_script(parsed.text, parsed.filename, parsed.page_count)
                st.success(f"Loaded {parsed.filename}" + (f" — {parsed.page_count} pages" if parsed.page_count else ""))
                if len(parsed.text) < 100:
                    st.warning("Very little text was extracted. If this is a scanned PDF, convert it to a text-based PDF or paste the script text.")
            except Exception as exc:
                st.error(str(exc))

    with paste_tab:
        pasted = st.text_area("Paste screenplay text", value=st.session_state.script_text if st.session_state.source_name == "Pasted Script" else "", height=320, placeholder="INT. UNIVERSITY LIBRARY – DAY\n\nA student enters...")
        if st.button("Use pasted script", use_container_width=True):
            set_script(pasted, "Pasted Script", None)
            st.success("Pasted script loaded.")

    with sample_tab:
        sample_map = {
            "Mystery Short Film — The Last Study Room": SAMPLES / "mystery_short.txt",
            "University Romance — Bad Joke": SAMPLES / "romance_short.txt",
            "Web Series — Frame by Frame": SAMPLES / "web_series.txt",
        }
        choice = st.selectbox("Choose a sample", list(sample_map.keys()))
        preview = read_sample(sample_map[choice])
        st.code(preview[:1800] + ("\n..." if len(preview) > 1800 else ""), language=None)
        if st.button("Load this sample", use_container_width=True):
            set_script(preview, choice, None)
            st.success("Sample loaded. Configure the analysis below.")

    if st.session_state.script_text:
        st.markdown("### Analysis settings")
        c1, c2, c3 = st.columns(3)
        with c1:
            title_hint = st.text_input("Script title (optional)", value="")
        with c2:
            script_type = st.selectbox("Script type", SCRIPT_TYPES)
        with c3:
            language = st.selectbox("Language", LANGUAGES)

        with st.expander("AI model settings"):
            model = st.text_input("OpenAI model", value=get_setting("OPENAI_MODEL", DEFAULT_MODEL), help="Default is cost-conscious GPT-5.6 Luna. You can change this in Streamlit secrets or .env/environment variables.")
            st.caption("Your extracted screenplay text is sent to the configured OpenAI model for analysis. This project calls the Responses API with store=False.")

        st.caption(f"Loaded source: {st.session_state.source_name or 'Script'} • {len(st.session_state.script_text):,} characters")
        api_key = get_setting("OPENAI_API_KEY")
        if not api_key:
            st.warning("OPENAI_API_KEY is not configured. Add it to Streamlit Secrets before running AI analysis.")

        if st.button("🎬 Analyse Script", type="primary", use_container_width=True, disabled=not bool(api_key)):
            with st.status("CineVora is reading your screenplay…", expanded=True) as status:
                try:
                    st.write("Detecting script type, genre, characters and scenes…")
                    st.write("Analysing structure, dialogue, pacing and visual storytelling…")
                    st.write("Preparing student-friendly feedback and next steps…")
                    result = analyse_script(
                        st.session_state.script_text,
                        api_key=api_key,
                        model=model.strip() or DEFAULT_MODEL,
                        script_type_hint=script_type,
                        language_hint=language,
                        title_hint=title_hint,
                        page_count=st.session_state.source_pages,
                    )
                    st.session_state.analysis = result
                    status.update(label="Analysis complete", state="complete", expanded=False)
                except Exception as exc:
                    status.update(label="Analysis failed", state="error", expanded=True)
                    st.error(f"Could not analyse this script: {exc}")

    if st.session_state.analysis:
        render_results(st.session_state.analysis)


def render_results(data):
    st.markdown("<div class='cv-divider'></div>", unsafe_allow_html=True)
    st.markdown("## Analysis Results")
    ov = data.get("overview", {})
    scores = data.get("scores", {})

    c1, c2, c3, c4 = st.columns([1.1, 1, 1, 1])
    with c1:
        st.markdown(f"<div class='cv-card'><div class='cv-muted'>Overall Creative Score</div><div class='cv-score'>{scores.get('overall', 0)}</div><div class='cv-muted'>/ 100</div></div>", unsafe_allow_html=True)
    with c2:
        st.metric("Script Type", ov.get("script_type", "—"))
        st.metric("Genre", ov.get("genre", "—"))
    with c3:
        st.metric("Scenes", ov.get("scene_count", 0))
        st.metric("Characters", ov.get("character_count", 0))
    with c4:
        st.metric("Duration", ov.get("estimated_duration", "—"))
        st.metric("Format", data.get("screenplay_format", {}).get("status", "—"))

    st.caption("AI scores are guidance, not academic grades. Screenplay formatting does not affect the Overall Creative Score.")

    tabs = st.tabs(["Overview", "Structure", "Characters", "Dialogue", "Scenes", "Pacing", "Originality", "Show vs Tell", "Format", "Final Feedback"])

    with tabs[0]:
        st.markdown(f"### {ov.get('title', 'Untitled Script')}")
        st.markdown(chips([ov.get("script_type", ""), ov.get("genre", ""), *ov.get("supporting_genres", []), ov.get("language", "")]), unsafe_allow_html=True)
        st.markdown("#### Story Summary")
        st.write(ov.get("summary", ""))
        st.markdown("#### Main Theme")
        st.write(ov.get("theme", ""))
        st.markdown("#### Story at a glance")
        a, b = st.columns(2)
        a.markdown(f"**Main Character:** {ov.get('main_character', '—')}  \n**Goal:** {ov.get('goal', '—')}")
        b.markdown(f"**Main Problem:** {ov.get('main_problem', '—')}  \n**Outcome:** {ov.get('outcome', '—')}")
        st.markdown("#### Locations")
        st.markdown(chips(ov.get("locations", [])), unsafe_allow_html=True)

    with tabs[1]:
        structure = data.get("structure", {})
        st.markdown(f"### {status_icon(structure.get('overall_status'))} Story / Series Structure — {structure.get('overall_status', '')}")
        st.write(structure.get("summary", ""))
        learn_expander("Story Structure")
        learn_expander("Turning Point")
        for beat in structure.get("beats", []):
            with st.expander(f"{status_icon(beat.get('status'))} {beat.get('name')} — {beat.get('status')}"):
                st.markdown(f"**What happens:** {beat.get('evidence', '')}")
                st.markdown(f"**Feedback:** {beat.get('feedback', '')}")
        if structure.get("episodes"):
            st.markdown("### Episode Structure")
            for ep in structure.get("episodes", []):
                with st.expander(ep.get("episode", "Episode")):
                    st.markdown(f"**Opening:** {ep.get('opening','')}")
                    st.markdown(f"**Main Event:** {ep.get('main_event','')}")
                    st.markdown(f"**Conflict:** {ep.get('conflict','')}")
                    st.markdown(f"**Character Development:** {ep.get('character_development','')}")
                    st.markdown(f"**Ending / Hook:** {ep.get('ending_hook','')}")

    with tabs[2]:
        st.markdown("### Main Character Analysis")
        learn_expander("Character Motivation")
        learn_expander("Character Arc")
        for ch in data.get("characters", []):
            with st.expander(f"{ch.get('name')} — {ch.get('role')}"):
                c1, c2 = st.columns(2)
                c1.markdown(f"**Goal**  \n{ch.get('goal','')}  \n\n**Motivation**  \n{ch.get('motivation','')}  \n\n**Conflict**  \n{ch.get('conflict','')}")
                c2.markdown(f"**Strength**  \n{ch.get('strength','')}  \n\n**Weakness**  \n{ch.get('weakness','')}  \n\n**Development / Arc**  \n{ch.get('development','')} → {ch.get('arc','')}")

    with tabs[3]:
        dialogue = data.get("dialogue", {})
        st.markdown(f"### Dialogue — {dialogue.get('overall_status','')}")
        st.write(dialogue.get("summary", ""))
        learn_expander("Dialogue")
        learn_expander("Exposition")
        for f in dialogue.get("findings", []):
            with st.expander(f"{status_icon(f.get('status'))} {f.get('category')} — {f.get('status')}"):
                if f.get("example"):
                    st.markdown(f"**Short script example:** “{f.get('example')}”")
                st.markdown(f"**Problem / observation:** {f.get('problem','')}")
                st.markdown(f"**Why it matters:** {f.get('why_it_matters','')}")
                st.markdown(f"**Possible improvement:** {f.get('suggestion','')}")

    with tabs[4]:
        st.markdown("### Important Scene Analysis")
        if not data.get("scenes"):
            st.info("No reliable scene-level analysis was produced.")
        for s in data.get("scenes", []):
            label = f"Scene {s.get('scene_number')} — {s.get('heading') or 'Untitled'} • {s.get('importance')} importance"
            with st.expander(label):
                st.markdown(f"**Purpose:** {s.get('purpose','')}")
                st.markdown(f"**Characters:** {', '.join(s.get('characters', [])) or '—'}")
                st.markdown(f"**Conflict:** {s.get('conflict','')}")
                st.markdown(f"**What works:** {s.get('what_works','')}")
                st.markdown(f"**Needs attention:** {s.get('problem','')}")
                st.markdown(f"**Suggestion:** {s.get('suggestion','')}")

    with tabs[5]:
        p = data.get("pacing", {})
        st.markdown(f"### {status_icon(p.get('overall'))} Overall Pacing — {p.get('overall','')}")
        learn_expander("Pacing")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Beginning", p.get("beginning", "—"))
        c2.metric("Middle", p.get("middle", "—"))
        c3.metric("Climax", p.get("climax", "—"))
        c4.metric("Ending", p.get("ending", "—"))
        st.write(p.get("explanation", ""))
        if p.get("slow_sections"):
            st.markdown("**Slower sections:**")
            for item in p.get("slow_sections", []): st.write("•", item)
        if p.get("rushed_sections"):
            st.markdown("**Rushed sections:**")
            for item in p.get("rushed_sections", []): st.write("•", item)

    with tabs[6]:
        o = data.get("originality", {})
        st.markdown(f"### Originality Guidance — {o.get('score',0)}/100")
        st.write(o.get("explanation", ""))
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Familiar elements**")
            for item in o.get("familiar_elements", []): st.write("•", item)
        with c2:
            st.markdown("**Distinctive elements**")
            for item in o.get("distinctive_elements", []): st.write("•", item)
        st.caption("This is not a claim that the idea has never existed. It evaluates how distinctive the execution feels within the supplied script.")

    with tabs[7]:
        svt = data.get("show_vs_tell", {})
        st.markdown("### Show vs Tell")
        learn_expander("Show vs Tell")
        st.markdown("#### 🟢 Strong visual storytelling")
        for item in svt.get("strong_visual_moments", []): st.write("•", item)
        st.markdown("#### 🟡 Possible telling")
        for item in svt.get("telling_moments", []):
            with st.expander(item.get("example", "Moment")):
                st.markdown(f"**Why:** {item.get('why','')}")
                st.markdown(f"**Try:** {item.get('suggestion','')}")

    with tabs[8]:
        fmt = data.get("screenplay_format", {})
        st.markdown(f"### {status_icon(fmt.get('status'))} Screenplay Format — {fmt.get('status','')}")
        st.success("This section does NOT affect the Overall Creative Score.")
        learn_expander("Screenplay Formatting")
        for item in fmt.get("strengths", []): st.write("✓", item)
        for issue in fmt.get("issues", []):
            with st.expander(f"⚠ {issue.get('type','Formatting issue')}"):
                if issue.get("example"): st.markdown(f"**Current example:** {issue.get('example')}")
                st.markdown(f"**Why:** {issue.get('explanation','')}")
                st.markdown(f"**Cleaner convention:** {issue.get('correction','')}")
        if fmt.get("confidence_note"):
            st.caption(fmt.get("confidence_note"))

    with tabs[9]:
        st.markdown("### Final Feedback")
        final = data.get("final_feedback", {})
        st.write(final.get("summary", ""))

        st.markdown("#### What Works")
        for item in data.get("strengths", [])[:5]:
            st.markdown(f"**✓ {item.get('title')}** — {item.get('explanation')}")

        st.markdown("#### Needs Improvement")
        for item in data.get("weaknesses", [])[:5]:
            st.markdown(f"**⚠ {item.get('title')}** — {item.get('explanation')}")

        st.markdown("#### AI Improvement Suggestions")
        for i, item in enumerate(data.get("improvement_suggestions", [])[:5], 1):
            with st.expander(f"{i}. {item.get('problem','Improvement')}"):
                st.markdown(f"**Why:** {item.get('why','')}")
                st.markdown(f"**How to improve:** {item.get('how_to_improve','')}")
                if item.get("example"): st.markdown(f"**Example:** {item.get('example')}")

        st.markdown("#### Top 3 Next Steps")
        labels = ["🥇 Fix First", "🥈 Fix Next", "🥉 Polish Last"]
        for i, step in enumerate(final.get("next_steps", [])[:3]):
            st.markdown(f"### {labels[i] if i < len(labels) else f'Priority {i+1}'}")
            st.write(step)

        st.markdown("#### Export Student Report")
        d1, d2 = st.columns(2)
        title = ov.get("title", "script").strip().replace(" ", "_") or "script"
        d1.download_button("Download JSON Analysis", data=download_json(data), file_name=f"{title}_cinevora_analysis.json", mime="application/json", use_container_width=True)
        try:
            pdf = build_pdf_report(data)
            d2.download_button("Download PDF Report", data=pdf, file_name=f"{title}_cinevora_report.pdf", mime="application/pdf", use_container_width=True)
        except Exception as exc:
            d2.warning(f"PDF export unavailable: {exc}")


def learn_page():
    st.markdown("## Learn Screenwriting Basics")
    st.write("Short explanations designed to support the analysis — not a giant filmmaking textbook.")
    for topic, item in LEARNING_TOPICS.items():
        with st.expander(topic):
            st.markdown(f"**Definition:** {item['definition']}")
            st.markdown(f"**Simple example:** {item['example']}")
            st.markdown(f"**Common mistake:** {item['mistake']}")
            st.markdown(f"**Quick tip:** {item['tip']}")


def about_page():
    st.markdown("## About CineVora AI")
    st.write("CineVora AI is a screenplay analysis and learning assistant for university students and emerging filmmakers. Its purpose is to help writers understand their own work, not replace their creative decisions.")
    st.markdown("### Core rule")
    st.markdown("**Analyse → Explain → Teach → Suggest → Student decides.**")
    st.markdown("### Score fairness")
    st.write("Storytelling quality and screenplay formatting are intentionally separated. A script can receive strong creative feedback even when the writer is still learning professional formatting.")
    if st.button("Replay cinematic intro"):
        render_intro(ASSETS / "cinematic_intro.wav")


if nav == "Home":
    home_page()
elif nav == "Analyse":
    analyse_page()
elif nav == "Learn":
    learn_page()
else:
    about_page()
