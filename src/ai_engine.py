from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from .config import DEFAULT_MODEL, MAX_CHARACTERS, MAX_SCENE_ANALYSIS, MAX_SCRIPT_CHARS
from .schema import analysis_schema


SYSTEM_INSTRUCTIONS = f"""
You are CineVora AI, a screenplay analysis and learning assistant designed for university students and emerging filmmakers.

Your job is to ANALYSE, EXPLAIN, TEACH, and SUGGEST. Do not write the student's entire film for them.
Use clear student-friendly language. Avoid unnecessary industry jargon. When a technical term is unavoidable, explain it simply.

IMPORTANT EVALUATION RULES:
1. Screenplay formatting must NEVER reduce the creative Overall Script Score.
2. Creative score categories are Story, Structure, Characters, Dialogue, Pacing, and Originality only.
3. Formatting is a separate learning assessment: Good / Mostly Good / Learning Stage / Needs Improvement.
4. A beginner with non-standard formatting can still have a strong story score.
5. If formatting makes extraction ambiguous, mention lower analysis confidence instead of reducing creative score.
6. Originality is an evaluation of distinctive execution, combinations, perspective, conflict, or character treatment. Never claim an idea has never existed before and never claim plagiarism based only on similarity.
7. Strengths and weaknesses: maximum 5 each, prioritise the most important ones.
8. Improvement suggestions: maximum 5. Use Problem -> Why -> How to improve -> brief example when useful.
9. Final next steps: exactly 3 priorities when possible: Fix First, Fix Next, Polish Last.
10. Scene analysis: select up to {MAX_SCENE_ANALYSIS} important scenes, not every scene in a long script.
11. Character analysis: focus on up to {MAX_CHARACTERS} important characters.
12. Dialogue examples must be short. Do not reproduce large sections of the screenplay.
13. For a Web Series, analyse overall series structure and add episode structure entries when episodes are clearly identifiable.
14. Adapt story structure to script type:
    - Short Film: Beginning, Conflict, Development, Turning Point, Climax, Ending.
    - Feature Film: Setup, Main Conflict, Development, Major Turning Point, Climax, Resolution.
    - Web Series: Series Setup, Main Conflict, Development, Major Reveal/Change, Final Conflict, Resolution; plus episode-level opening, main event, conflict, character development, ending hook.
    - Pilot: Opening Hook, World Introduction, Main Character, Main Problem, Episode Conflict, Ending Hook, Series Potential.
15. Do not punish unconventional style if the narrative intention remains understandable.
""".strip()


def _trim_script(text: str) -> tuple[str, str]:
    if len(text) <= MAX_SCRIPT_CHARS:
        return text, "Full script supplied."

    third = MAX_SCRIPT_CHARS // 3
    head = text[:third]
    mid_start = max(0, len(text) // 2 - third // 2)
    middle = text[mid_start:mid_start + third]
    tail = text[-third:]
    compact = head + "\n\n[...MIDDLE SAMPLE...]\n\n" + middle + "\n\n[...ENDING SAMPLE...]\n\n" + tail
    return compact, "The script exceeded the configured input limit, so beginning, middle, and ending samples were analysed."


def _normalise_scores(data: dict[str, Any]) -> dict[str, Any]:
    scores = data.get("scores", {})
    keys = ["story", "structure", "characters", "dialogue", "pacing", "originality"]
    values = []
    for key in keys:
        value = scores.get(key, 0)
        try:
            value = max(0, min(100, int(round(float(value)))))
        except (TypeError, ValueError):
            value = 0
        scores[key] = value
        values.append(value)

    scores["overall"] = round(sum(values) / len(values)) if values else 0
    data["scores"] = scores

    fmt = data.setdefault("screenplay_format", {})
    fmt["affects_overall_score"] = False
    return data


def analyse_script(
    script_text: str,
    *,
    api_key: str,
    model: str = DEFAULT_MODEL,
    script_type_hint: str = "Auto Detect",
    language_hint: str = "Auto Detect",
    title_hint: str = "",
    page_count: int | None = None,
) -> dict[str, Any]:
    if not api_key:
        raise ValueError("OPENAI_API_KEY is missing.")
    if not script_text or len(script_text.strip()) < 80:
        raise ValueError("The script is too short to analyse. Add more screenplay text.")

    client = OpenAI(api_key=api_key)
    compact_script, coverage_note = _trim_script(script_text.strip())

    user_prompt = f"""
Analyse the screenplay below for a university student.

USER HINTS
Title hint: {title_hint or 'Not provided'}
Script type hint: {script_type_hint}
Language hint: {language_hint}
Known page count: {page_count if page_count is not None else 'Unknown'}
Coverage note: {coverage_note}

Return evidence-based feedback grounded in the supplied screenplay. If something cannot be determined, say it is unclear rather than inventing details.

SCREENPLAY
--- BEGIN SCREENPLAY ---
{compact_script}
--- END SCREENPLAY ---
""".strip()

    response = client.responses.create(
        model=model,
        instructions=SYSTEM_INSTRUCTIONS,
        input=user_prompt,
        reasoning={"effort": "low"},
        text={
            "verbosity": "low",
            "format": {
                "type": "json_schema",
                "name": "cinevora_script_analysis",
                "strict": True,
                "schema": analysis_schema(),
            },
        },
        max_output_tokens=18000,
        store=False,
    )

    if not response.output_text:
        raise RuntimeError("The AI returned no analysis text.")

    data = json.loads(response.output_text)
    data = _normalise_scores(data)
    data["analysis_meta"] = {
        "model": model,
        "coverage_note": coverage_note,
    }
    return data
