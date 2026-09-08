# CineVora AI — University Screenplay Analysis App

A complete Streamlit screenplay analysis and learning app for university students and emerging filmmakers.

## Included features

- PDF / DOCX / TXT upload and paste-script input
- Included sample scripts
- Script type detection: Short Film / Feature Film / Web Series / Pilot
- Script Overview and Genre Detection
- Adaptive Story / Series Structure
- Episode Structure for Web Series
- Character Analysis: role, goal, motivation, conflict, development and arc
- Dialogue Analysis: natural, long, unnecessary, repetitive, exposition and character voice
- Important Scene Analysis
- Pacing Analysis: Slow / Balanced / Rushed
- Originality guidance score and explanation
- Show vs Tell analysis
- Student Learning Mode ("Why?")
- Screenplay Format Check, kept separate from creative scoring
- Strengths & Weaknesses
- Problem → Why → How to Improve feedback
- Overall Creative Score (0–100)
- Final Feedback + Top 3 Next Steps
- JSON and PDF report export
- Cinematic CineVora AI opening animation
- Original generated cinematic intro sound asset

## Important scoring rule

Screenplay formatting **does not affect the Overall Creative Score**. The creative score is the average of Story, Structure, Characters, Dialogue, Pacing and Originality. Formatting is a separate learning assessment for beginners.

## 1. Install

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

macOS / Linux:

```bash
source .venv/bin/activate
```

Then:

```bash
pip install -r requirements.txt
```

## 2. Add your OpenAI API key

For local Streamlit, create:

`.streamlit/secrets.toml`

```toml
OPENAI_API_KEY = "sk-your-key-here"
OPENAI_MODEL = "gpt-5.6-luna"
```

Do **not** commit `secrets.toml` to GitHub.

The app uses the OpenAI Responses API with Structured Outputs and `store=False`. The default model in this project is `gpt-5.6-luna` because it supports long context and structured outputs while targeting cost-sensitive workloads. You can change `OPENAI_MODEL` without changing the app code.

## 3. Run

```bash
streamlit run app.py
```

## 4. Deploy to Streamlit Community Cloud

Upload these project files to GitHub, excluding `.streamlit/secrets.toml`.

In Streamlit Cloud:

1. Create a new app from the repository.
2. Set the main file to `app.py`.
3. Open App settings → Secrets.
4. Add:

```toml
OPENAI_API_KEY = "sk-your-key-here"
OPENAI_MODEL = "gpt-5.6-luna"
```

5. Deploy.

## Cinematic intro + music

The first app load displays a full-screen CineVora AI cinematic animation that fades automatically after about 6 seconds. The included `assets/cinematic_intro.wav` is original, procedurally generated audio.

The app attempts to autoplay the sound. Modern browsers can block audible autoplay before the user has interacted with the page. This is a browser security rule, not a Streamlit bug. The visual intro still transitions automatically even when audio autoplay is blocked.

## Project structure

```text
cinevora_ai/
├── app.py
├── requirements.txt
├── README.md
├── assets/
│   └── cinematic_intro.wav
├── samples/
│   ├── mystery_short.txt
│   ├── romance_short.txt
│   └── web_series.txt
├── src/
│   ├── __init__.py
│   ├── ai_engine.py
│   ├── config.py
│   ├── parser.py
│   ├── report.py
│   ├── schema.py
│   └── ui.py
├── tests/
│   ├── test_parser.py
│   └── test_score.py
└── .streamlit/
    ├── config.toml
    └── secrets.toml.example
```

## Notes

- Text-based PDFs work best. Image-only/scanned PDFs need OCR before upload.
- Very long scripts are supported; if the input exceeds the project's configured character limit, CineVora samples the beginning, middle and ending and reports that coverage limitation.
- The AI does not automatically rewrite the whole screenplay. Its purpose is to analyse, explain, teach and suggest.
