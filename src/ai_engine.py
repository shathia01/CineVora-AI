from __future__ import annotations

import math
import re
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any

from .config import MAX_CHARACTERS, MAX_SCENE_ANALYSIS


# -----------------------------------------------------------------------------
# CineVora Free Engine
# -----------------------------------------------------------------------------
# This module intentionally uses no paid API and sends no screenplay text to an
# external service. It uses deterministic screenplay/NLP heuristics so it can
# run on Streamlit Community Cloud for free (subject to Streamlit's own limits).
# -----------------------------------------------------------------------------

SCENE_RE = re.compile(
    r"^(?:\d+\s*)?(?:INT\.?|EXT\.?|INT\.?/EXT\.?|EXT\.?/INT\.?|I/E)\s*[.\- ]\s*.+$",
    re.IGNORECASE,
)
EPISODE_RE = re.compile(r"^EPISODE\s+(\d+|[IVX]+)\b.*$", re.IGNORECASE)
META_RE = re.compile(r"^(TITLE|TYPE|GENRE|LANGUAGE|EPISODES?|WRITTEN BY|DURATION)\s*:", re.IGNORECASE)
TRANSITION_WORDS = {
    "CUT TO:", "CUT TO BLACK.", "CUT TO BLACK", "FADE IN:", "FADE OUT:",
    "DISSOLVE TO:", "SMASH CUT:", "MATCH CUT:", "THE END", "END"
}
STOPWORDS = {
    "the", "and", "that", "with", "from", "into", "this", "then", "they", "their",
    "there", "here", "have", "has", "had", "were", "was", "are", "for", "but", "not",
    "you", "your", "his", "her", "she", "him", "its", "our", "out", "all", "one", "two",
    "just", "like", "what", "when", "where", "why", "how", "who", "can", "could", "would",
    "should", "will", "now", "after", "before", "again", "back", "over", "under", "about",
    "through", "toward", "towards", "looks", "look", "says", "say", "walks", "walk", "room",
    "day", "night", "morning", "evening", "later", "inside", "outside"
}

GENRE_KEYWORDS = {
    "Mystery / Thriller": ["mystery", "locked", "missing", "secret", "unknown", "blood", "dead", "death", "shadow", "door", "strange", "reveal", "truth"],
    "Horror": ["ghost", "haunted", "horror", "blood", "scream", "zombie", "corpse", "fear", "dark", "terrified", "monster"],
    "Romance": ["love", "romance", "kiss", "crush", "date", "follow request", "smile", "relationship", "heart", "boyfriend", "girlfriend"],
    "Comedy": ["joke", "laugh", "funny", "comedy", "tease", "prank", "idiot", "dei", "macha"],
    "Coming-of-Age Drama": ["university", "college", "career", "dream", "future", "parents", "father", "mother", "student", "exam", "friends", "life path"],
    "Drama": ["family", "argument", "cry", "sorry", "leave", "pressure", "conflict", "relationship", "future"],
    "Action": ["fight", "chase", "gun", "attack", "run", "punch", "explosion", "escape"],
}

VISUAL_VERBS = {
    "enters", "leaves", "turns", "opens", "closes", "walks", "runs", "sits", "stands", "freezes",
    "looks", "stares", "smiles", "cries", "drops", "grabs", "pulls", "pushes", "reaches", "places",
    "holds", "lowers", "raises", "steps", "moves", "falls", "locks", "unlocks", "trembles", "breathing"
}
TELLING_MARKERS = [
    "i feel", "i am scared", "i'm scared", "i am afraid", "i'm afraid", "i love you", "i hate",
    "because", "the reason is", "you remember", "remember when", "as you know", "let me explain",
    "what happened was", "two years ago", "last year", "since then", "my dream is", "i want to"
]
CONFLICT_WORDS = {
    "but", "no", "can't", "cannot", "won't", "stop", "leave", "locked", "fight", "argument", "pressure",
    "against", "problem", "fail", "fear", "afraid", "secret", "truth", "future", "dream", "father", "mother"
}
CLIMAX_WORDS = {"finally", "reveal", "truth", "fight", "confront", "face", "escape", "breaks", "dies", "death", "kiss", "decides", "chooses", "unlock"}


@dataclass
class Scene:
    number: int
    heading: str
    body_lines: list[str]
    start_line: int

    @property
    def text(self) -> str:
        return "\n".join(self.body_lines).strip()

    @property
    def words(self) -> int:
        return len(re.findall(r"\b\w+[’']?\w*\b", self.text))


@dataclass
class DialogueBlock:
    character: str
    text: str
    line_index: int

    @property
    def words(self) -> int:
        return len(self.text.split())


def _clip(text: str, limit: int = 150) -> str:
    clean = re.sub(r"\s+", " ", (text or "").strip())
    if len(clean) <= limit:
        return clean
    return clean[: limit - 1].rstrip() + "…"


def _meta_value(text: str, key: str) -> str:
    m = re.search(rf"^{re.escape(key)}\s*:\s*(.+)$", text, re.IGNORECASE | re.MULTILINE)
    return m.group(1).strip() if m else ""


def _is_scene_heading(line: str) -> bool:
    return bool(SCENE_RE.match(line.strip()))


def _base_character_cue(line: str) -> str:
    cue = re.sub(r"\([^)]*\)", "", line).strip()
    cue = re.sub(r"\s+", " ", cue)
    return cue


def _is_character_cue(lines: list[str], idx: int) -> bool:
    line = lines[idx].strip()
    if not line or _is_scene_heading(line) or META_RE.match(line):
        return False
    if line.upper() in TRANSITION_WORDS or line.upper().startswith("END EPISODE"):
        return False
    if len(line) > 55 or line.endswith(('.', '!', '?', ':')):
        return False
    letters = [c for c in line if c.isalpha()]
    if not letters or not all(c.isupper() for c in letters):
        return False
    # A cue normally has dialogue soon after it.
    for j in range(idx + 1, min(idx + 4, len(lines))):
        nxt = lines[j].strip()
        if not nxt:
            continue
        if _is_scene_heading(nxt) or META_RE.match(nxt):
            return False
        if nxt.upper() in TRANSITION_WORDS:
            return False
        return True
    return False


def _extract_dialogue(lines: list[str]) -> list[DialogueBlock]:
    blocks: list[DialogueBlock] = []
    i = 0
    while i < len(lines):
        if not _is_character_cue(lines, i):
            i += 1
            continue
        char = _base_character_cue(lines[i])
        parts: list[str] = []
        j = i + 1
        while j < len(lines):
            raw = lines[j].strip()
            if not raw:
                if parts:
                    break
                j += 1
                continue
            if _is_scene_heading(raw) or META_RE.match(raw) or raw.upper() in TRANSITION_WORDS or raw.upper().startswith("END EPISODE"):
                break
            if _is_character_cue(lines, j):
                break
            # Parentheticals can remain attached to dialogue for context.
            parts.append(raw)
            j += 1
        if parts:
            blocks.append(DialogueBlock(char, " ".join(parts), i))
        i = max(j, i + 1)
    return blocks


def _split_scenes(lines: list[str]) -> list[Scene]:
    positions = [(i, line.strip()) for i, line in enumerate(lines) if _is_scene_heading(line)]
    if not positions:
        # Treat the entire screenplay as one scene so the rest of the analysis can still work.
        body = [x for x in lines if x.strip() and not META_RE.match(x.strip())]
        return [Scene(1, "Unformatted / Scene heading not detected", body, 0)] if body else []

    scenes: list[Scene] = []
    for n, (idx, heading) in enumerate(positions, start=1):
        end = positions[n][0] if n < len(positions) else len(lines)
        scenes.append(Scene(n, heading, lines[idx + 1:end], idx))
    return scenes


def _extract_locations(scenes: list[Scene]) -> list[str]:
    out: list[str] = []
    for scene in scenes:
        h = re.sub(r"^(?:\d+\s*)?(?:INT\.?|EXT\.?|INT\.?/EXT\.?|EXT\.?/INT\.?|I/E)\s*[.\- ]\s*", "", scene.heading, flags=re.IGNORECASE)
        # Screenplay headings usually end with a time-of-day after a dash.
        loc = re.split(r"\s+[–—-]\s+(?:DAY|NIGHT|MORNING|AFTERNOON|EVENING|LATER|CONTINUOUS|SUNSET|DAWN|DUSK)\b", h, maxsplit=1, flags=re.IGNORECASE)[0]
        loc = loc.strip(" .–—-")
        if loc and loc.lower() not in {x.lower() for x in out}:
            out.append(loc)
    return out[:20]


def _detect_language(text: str, hint: str) -> str:
    if hint and hint != "Auto Detect":
        return hint
    tamil_chars = len(re.findall(r"[\u0B80-\u0BFF]", text))
    if tamil_chars > 20:
        return "Tamil"
    lower = text.lower()
    tanglish = ["enna", "ennaku", "dey", "dei", "macha", "irukku", "vanthu", "pannu", "paaru", "enge", "illa", "venum", "apdi", "aana", "seri"]
    bm = ["saya", "awak", "tidak", "kerana", "dengan", "untuk", "yang", "boleh", "mahu", "universiti"]
    if sum(lower.count(w) for w in tanglish) >= 3:
        return "Tanglish"
    if sum(lower.count(w) for w in bm) >= 4:
        return "Bahasa Malaysia"
    return "English"


def _detect_script_type(text: str, hint: str, page_count: int | None, scenes: list[Scene]) -> str:
    if hint and hint != "Auto Detect":
        return hint
    explicit = _meta_value(text, "TYPE").upper()
    if "WEB" in explicit or "SERIES" in explicit:
        return "Web Series"
    if "PILOT" in explicit:
        return "Pilot"
    if "FEATURE" in explicit:
        return "Feature Film"
    if "SHORT" in explicit:
        return "Short Film"
    if re.search(r"^EPISODE\s+\d+", text, re.IGNORECASE | re.MULTILINE):
        return "Web Series"
    if re.search(r"\bPILOT\b", text[:1200], re.IGNORECASE):
        return "Pilot"
    if page_count is not None:
        if page_count >= 55:
            return "Feature Film"
        if page_count <= 35:
            return "Short Film"
    words = len(text.split())
    if words > 12000 or len(scenes) > 45:
        return "Feature Film"
    return "Short Film"


def _detect_genre(text: str) -> tuple[str, list[str]]:
    explicit = _meta_value(text, "GENRE")
    if explicit:
        parts = [p.strip().title() for p in re.split(r"[/,|+]", explicit) if p.strip()]
        return (parts[0] if parts else explicit.title(), parts[1:3])

    lower = text.lower()
    scores: list[tuple[int, str]] = []
    for genre, words in GENRE_KEYWORDS.items():
        score = sum(lower.count(w) for w in words)
        scores.append((score, genre))
    scores.sort(reverse=True)
    main = scores[0][1] if scores and scores[0][0] > 0 else "Drama"
    supporting = [g for s, g in scores[1:] if s > 1 and g != main][:2]
    return main, supporting


def _infer_theme(text: str, genre: str) -> str:
    low = text.lower()
    if ("dream" in low or "future" in low or "cinema" in low or "director" in low) and any(x in low for x in ["father", "mother", "parents", "family", "job"]):
        return "Choosing a personal dream while facing family or social expectations."
    if any(x in low for x in ["fear", "afraid", "scared", "running"]) and any(x in low for x in ["face", "confront", "stay"]):
        return "Facing fear instead of allowing it to control your choices."
    if "Romance" in genre or "love" in low:
        return "Genuine connection grows through honesty and small human moments."
    if any(x in low for x in ["friend", "friends", "friendship"]):
        return "Friendship and support shape how the characters handle pressure and change."
    return "The script explores how a character responds to conflict and change."


def _infer_goal(main: str, dialogues: list[DialogueBlock], text: str, genre: str) -> str:
    candidates = [d for d in dialogues if d.character == main]
    for d in candidates:
        m = re.search(r"\b(?:I want|I need|I'm going to|I am going to|my dream is|one day I(?:'m| am)?)\b(.{0,100})", d.text, re.IGNORECASE)
        if m:
            phrase = _clip((m.group(0)).strip(" ."), 120)
            return phrase[0].upper() + phrase[1:] if phrase else "Pursue a clear personal objective."
    low = text.lower()
    if "director" in low or "cinema" in low or "film" in low:
        return "Pursue a filmmaking or creative goal."
    if "Romance" in genre:
        return "Understand or build an important personal connection."
    if "Horror" in genre or "Thriller" in genre:
        return "Understand the threat and get through the situation safely."
    return "Move toward the central objective established by the screenplay."


def _infer_problem(text: str, genre: str) -> str:
    low = text.lower()
    if ("dream" in low or "future" in low or "cinema" in low) and any(x in low for x in ["father", "mother", "parents", "job"]):
        return "Personal ambition clashes with family expectations and pressure about the future."
    if any(x in low for x in ["locked", "fear", "ghost", "haunted", "strange", "blood"]):
        return "An unsettling threat or unexplained situation disrupts the protagonist's normal goal."
    if "Romance" in genre:
        return "Uncertainty about feelings, trust, or communication complicates the relationship."
    if any(x in low for x in ["exam", "fail", "competition", "deadline"]):
        return "The protagonist faces pressure around an important test, deadline, or outcome."
    return "The protagonist meets resistance that makes the central goal harder to achieve."


def _last_story_line(lines: list[str]) -> str:
    for line in reversed(lines):
        s = line.strip()
        if not s or META_RE.match(s) or s.upper() in TRANSITION_WORDS or _is_character_cue(lines, lines.index(line) if line in lines else 0):
            continue
        if s.upper().startswith("END EPISODE"):
            return _clip(s.split(":", 1)[-1], 130)
        return _clip(s, 130)
    return "The ending should be reviewed for how clearly it resolves or extends the central conflict."


def _build_summary(main: str, second: str, locations: list[str], genre: str, problem: str, outcome: str) -> str:
    place = locations[0] if locations else "the story's main setting"
    if "Romance" in genre:
        partner = second or "another character"
        return f"{main} navigates a developing connection with {partner} around {place}. Their interactions build through small conversations and emotional uncertainty. {problem} The screenplay moves toward an ending that clarifies how the relationship has changed."
    if "Horror" in genre or "Thriller" in genre or "Mystery" in genre:
        return f"{main} enters or moves through {place} and encounters increasingly unsettling events. {problem} The tension escalates through visual details and reactions before the story reaches its final beat: {outcome}"
    return f"{main} moves through a story centered on {place}. {problem} The screenplay develops this pressure through scenes, relationships, and choices before reaching its ending: {outcome}"


def _structure_names(script_type: str) -> list[str]:
    if script_type == "Feature Film":
        return ["Setup", "Main Conflict", "Development", "Major Turning Point", "Climax", "Resolution"]
    if script_type == "Web Series":
        return ["Series Setup", "Main Conflict", "Development", "Major Reveal / Change", "Final Conflict", "Resolution"]
    if script_type == "Pilot":
        return ["Opening Hook", "World Introduction", "Main Character", "Main Problem", "Episode Conflict", "Ending Hook", "Series Potential"]
    return ["Beginning", "Conflict", "Development", "Turning Point", "Climax", "Ending"]


def _scene_excerpt(scene: Scene) -> str:
    parts = [x.strip() for i, x in enumerate(scene.body_lines) if x.strip() and not _is_character_cue(scene.body_lines, i)]
    if parts:
        return _clip(parts[0], 150)
    return scene.heading


def _analyse_structure(script_type: str, scenes: list[Scene], lines: list[str]) -> dict[str, Any]:
    names = _structure_names(script_type)
    if not scenes:
        return {"overall_status": "Unclear", "summary": "No clear scenes were detected.", "beats": [], "episodes": []}

    beats = []
    total = len(scenes)
    enough = total >= max(2, len(names) // 2)
    for i, name in enumerate(names):
        pos = 0 if len(names) == 1 else round(i * (total - 1) / (len(names) - 1))
        scene = scenes[min(pos, total - 1)]
        scene_low = scene.text.lower()
        status = "Present" if enough else "Unclear"
        if name in {"Conflict", "Main Conflict", "Main Problem", "Episode Conflict", "Final Conflict"}:
            if any(w in scene_low for w in CONFLICT_WORDS):
                status = "Clear"
        elif "Climax" in name or "Turning" in name or "Reveal" in name or "Hook" in name:
            if any(w in scene_low for w in CLIMAX_WORDS) or "?" in scene.text:
                status = "Clear"
            elif enough:
                status = "Present"
        elif i == 0 or i == len(names) - 1:
            status = "Clear" if scene.words > 8 else "Present"

        feedback = "This beat is identifiable from the script's progression."
        if status == "Unclear":
            feedback = "The beat is not strongly separated in free-mode detection. Consider making the change in goal, conflict, or direction clearer."
        elif "Turning" in name or "Reveal" in name:
            feedback = "Check that this moment changes what the protagonist knows, wants, or decides next."
        elif "Climax" in name:
            feedback = "The climax should contain the strongest confrontation, decision, or consequence of the central conflict."
        elif name in {"Ending", "Resolution"}:
            feedback = "Check that the ending gives a deliberate sense of resolution, consequence, or open-ended continuation."

        beats.append({"name": name, "status": status, "evidence": f"{scene.heading}: {_scene_excerpt(scene)}", "feedback": feedback})

    episodes = _episode_analysis(lines) if script_type == "Web Series" else []
    clear_count = sum(1 for b in beats if b["status"] in {"Clear", "Present"})
    overall = "Clear" if clear_count >= max(3, len(beats) - 1) else "Mostly Clear" if clear_count >= 3 else "Unclear"
    summary = f"Free mode detected {clear_count} of {len(beats)} major structure beats with usable evidence. Review the weaker beats as learning guidance rather than a strict formula."
    return {"overall_status": overall, "summary": summary, "beats": beats, "episodes": episodes}


def _episode_analysis(lines: list[str]) -> list[dict[str, str]]:
    starts = [(i, line.strip()) for i, line in enumerate(lines) if EPISODE_RE.match(line.strip())]
    out: list[dict[str, str]] = []
    for n, (idx, label) in enumerate(starts[:12]):
        end = starts[n + 1][0] if n + 1 < len(starts) else len(lines)
        chunk = [x.strip() for x in lines[idx + 1:end] if x.strip()]
        headings = [x for x in chunk if _is_scene_heading(x)]
        narrative = [x for x in chunk if not META_RE.match(x) and not _is_scene_heading(x) and not x.upper() in TRANSITION_WORDS]
        opening = _clip(next((x for x in narrative if not x.upper().startswith("END EPISODE")), headings[0] if headings else "Opening not clear"), 130)
        middle = _clip(narrative[len(narrative) // 2] if narrative else "Main event not clear", 130)
        conflict = _clip(next((x for x in narrative if any(w in x.lower() for w in CONFLICT_WORDS)), "Conflict is not strongly signposted in free mode."), 130)
        ending = next((x.split(":", 1)[-1].strip() for x in reversed(chunk) if x.upper().startswith("END EPISODE")), "Ending hook not explicitly labelled.")
        out.append({
            "episode": label,
            "opening": opening,
            "main_event": middle,
            "conflict": conflict,
            "character_development": "Review the episode's first and final character choices to confirm what changes emotionally or practically.",
            "ending_hook": _clip(ending, 150),
        })
    return out


def _character_context(name: str, lines: list[str], radius: int = 4) -> str:
    chunks = []
    for i, line in enumerate(lines):
        if name in line.upper():
            chunks.extend(lines[max(0, i - radius): min(len(lines), i + radius + 1)])
    return " ".join(chunks)


def _analyse_characters(char_counts: Counter, dialogues: list[DialogueBlock], lines: list[str], main: str, problem: str) -> list[dict[str, str]]:
    by_char: dict[str, list[DialogueBlock]] = defaultdict(list)
    for d in dialogues:
        by_char[d.character].append(d)
    out = []
    for idx, (name, count) in enumerate(char_counts.most_common(MAX_CHARACTERS)):
        context = _character_context(name, lines).lower()
        own = " ".join(d.text for d in by_char.get(name, []))
        goal = _infer_goal(name, by_char.get(name, []), context, "")
        if name != main and goal.startswith("Move toward"):
            goal = "Support, challenge, or influence the central character's decisions."
        motivation = "The script suggests this character is motivated by what is personally at stake in the conflict."
        if any(w in (own + " " + context).lower() for w in ["family", "father", "mother", "future", "job"]):
            motivation = "Concern about family, stability, or the future appears to influence this character's choices."
        elif any(w in (own + " " + context).lower() for w in ["friend", "help", "support"]):
            motivation = "Friendship and support appear to motivate this character's involvement."
        elif any(w in (own + " " + context).lower() for w in ["love", "like", "feel", "relationship"]):
            motivation = "Personal feelings and relationship uncertainty appear to motivate this character."

        conflict = problem if name == main else "This character is involved in or reacts to the central conflict, though free mode may not infer a separate internal conflict reliably."
        strength = "Has a clear presence in the screenplay and contributes to the scene dynamics." if count >= 2 else "Has an identifiable function in the scenes where they appear."
        weakness = "The character may need more distinctive choices or reactions to feel fully developed." if count < 3 else "Check whether the character's dialogue and choices remain distinct from other characters."
        occurrences = [d.line_index for d in by_char.get(name, [])]
        development = "Appears across multiple parts of the script, allowing room for visible development." if occurrences and max(occurrences) - min(occurrences) > max(8, len(lines) // 4) else "Development is concentrated in a limited section of the script."
        arc = "Beginning state → pressure or choice → later response. Confirm the change through actions, not only explanation." if name == main else "Supporting arc: influence / react / change in relation to the main conflict."
        out.append({
            "name": name,
            "role": "Protagonist" if idx == 0 else "Supporting Character",
            "goal": goal,
            "motivation": motivation,
            "conflict": conflict,
            "strength": strength,
            "weakness": weakness,
            "development": development,
            "arc": arc,
        })
    return out


def _analyse_dialogue(dialogues: list[DialogueBlock]) -> tuple[dict[str, Any], dict[str, float]]:
    if not dialogues:
        return {
            "overall_status": "Needs Attention",
            "summary": "No reliable screenplay dialogue blocks were detected. The story may still be understandable, but dialogue-specific feedback is limited.",
            "findings": [{
                "category": "Natural", "status": "Needs Attention", "example": "", "problem": "Dialogue cues were not reliably detected.",
                "why_it_matters": "CineVora needs a clear speaker/dialogue relationship to assess dialogue patterns.",
                "suggestion": "Use a character cue on its own line, followed by dialogue on the next line."
            }]
        }, {"long_ratio": 0.0, "expo_ratio": 0.0, "repeat_ratio": 0.0}

    lengths = [d.words for d in dialogues]
    avg = statistics.mean(lengths)
    long_blocks = [d for d in dialogues if d.words >= 32]
    expo_blocks = [d for d in dialogues if d.words >= 16 and any(m in d.text.lower() for m in TELLING_MARKERS)]
    norms = [re.sub(r"[^a-z0-9 ]", "", d.text.lower()).strip() for d in dialogues]
    counts = Counter(n for n in norms if len(n.split()) >= 3)
    repeated = {n for n, c in counts.items() if c > 1}
    repeated_blocks = [d for d, n in zip(dialogues, norms) if n in repeated]

    by_char = defaultdict(list)
    for d in dialogues:
        by_char[d.character].append(d.words)
    voice_means = [statistics.mean(v) for v in by_char.values() if len(v) >= 2]
    voice_distinct = len(voice_means) >= 2 and (max(voice_means) - min(voice_means) >= 4)

    findings = []
    natural_good = avg <= 22 and (len(long_blocks) / len(dialogues)) <= 0.25
    findings.append({
        "category": "Natural", "status": "Good" if natural_good else "Needs Attention",
        "example": _clip(min(dialogues, key=lambda d: abs(d.words - min(avg, 12))).text, 120),
        "problem": "Dialogue generally uses manageable conversational lengths." if natural_good else "Several dialogue blocks are longer than typical conversational exchanges.",
        "why_it_matters": "Shorter exchanges often create more rhythm, reaction, and subtext on screen.",
        "suggestion": "Read the scene aloud and break essay-like speeches where a reaction, action, or interruption could carry part of the meaning."
    })

    if long_blocks:
        d = max(long_blocks, key=lambda x: x.words)
        findings.append({"category": "Long", "status": "Needs Attention", "example": _clip(d.text, 135), "problem": f"A dialogue block runs about {d.words} words.", "why_it_matters": "Long uninterrupted speeches can slow a scene unless the moment is intentionally a monologue.", "suggestion": "Break repeated ideas into shorter exchanges and allow another character's reaction or action to carry part of the scene."})
    else:
        findings.append({"category": "Long", "status": "Good", "example": "", "problem": "No unusually long dialogue blocks were detected.", "why_it_matters": "This helps maintain scene rhythm.", "suggestion": "Keep checking that longer speeches are earned by the dramatic moment."})

    if expo_blocks:
        d = expo_blocks[0]
        findings.append({"category": "Too Much Exposition", "status": "Needs Attention", "example": _clip(d.text, 135), "problem": "Some dialogue combines explanation with a relatively long speech.", "why_it_matters": "When characters explain information directly, the scene can feel written for the audience rather than lived by the characters.", "suggestion": "Move part of the information into behaviour, conflict, visual detail, or a later shorter line."})
    else:
        findings.append({"category": "Too Much Exposition", "status": "Good", "example": "", "problem": "No strong exposition-heavy pattern was detected by the free engine.", "why_it_matters": "This suggests information is not consistently delivered in long explanatory speeches.", "suggestion": "Still review any backstory-heavy scenes manually; heuristic detection can miss subtle exposition."})

    if repeated_blocks:
        d = repeated_blocks[0]
        findings.append({"category": "Repetitive", "status": "Needs Attention", "example": _clip(d.text, 120), "problem": "The same or very similar dialogue appears more than once.", "why_it_matters": "Repeated information can make a scene feel longer without adding new conflict or emotion.", "suggestion": "Keep the strongest version and make later lines add new information, escalation, or subtext."})
    else:
        findings.append({"category": "Repetitive", "status": "Good", "example": "", "problem": "No exact repeated dialogue pattern was detected.", "why_it_matters": "Each exchange is more likely to move the scene forward.", "suggestion": "Free mode checks obvious repetition; also review repeated ideas expressed with different wording."})

    findings.append({
        "category": "Character Voice", "status": "Good" if voice_distinct else "Needs Attention",
        "example": "", "problem": "Characters show different dialogue rhythms." if voice_distinct else "Dialogue rhythms are fairly similar across the main speaking characters.",
        "why_it_matters": "Distinct voice helps the audience recognise personality even without character names.",
        "suggestion": "Give major characters different habits: sentence length, humour, directness, hesitation, vocabulary, or what they avoid saying."
    })

    long_ratio = len(long_blocks) / len(dialogues)
    expo_ratio = len(expo_blocks) / len(dialogues)
    repeat_ratio = len(repeated_blocks) / len(dialogues)
    attention = sum(1 for f in findings if f["status"] == "Needs Attention")
    status = "Good" if attention <= 1 else "Mostly Good" if attention == 2 else "Needs Attention"
    summary = f"Detected {len(dialogues)} dialogue blocks across {len(by_char)} speaking characters. Average dialogue block length is about {avg:.0f} words."
    return {"overall_status": status, "summary": summary, "findings": findings}, {"long_ratio": long_ratio, "expo_ratio": expo_ratio, "repeat_ratio": repeat_ratio, "avg_words": avg}


def _scene_dialogues(scene: Scene, all_dialogues: list[DialogueBlock]) -> list[DialogueBlock]:
    start = scene.start_line
    # approximate end from scene body line count; + heading
    end = start + len(scene.body_lines) + 1
    return [d for d in all_dialogues if start <= d.line_index <= end]


def _scene_purpose(scene: Scene, pos: int, total: int) -> str:
    low = scene.text.lower()
    if pos == 0:
        return "Establish the setting, tone, and the character's starting situation."
    if pos == total - 1:
        return "Deliver the ending beat, consequence, resolution, or hook."
    if any(x in low for x in ["father", "mother", "parents", "argument", "future", "job"]):
        return "Develop interpersonal pressure and clarify what is at stake for the character."
    if any(x in low for x in ["reveal", "secret", "truth", "finds", "discovers", "appears"]):
        return "Introduce or reveal information that changes the audience's understanding."
    if any(x in low for x in ["kiss", "smile", "love", "follow", "laugh"]):
        return "Develop the relationship and change the emotional connection between characters."
    if any(x in low for x in ["locked", "fear", "blood", "door", "chair", "scream"]):
        return "Escalate tension and increase the character's immediate problem."
    return "Advance the story by adding information, conflict, or character interaction."


def _scene_conflict(scene: Scene) -> str:
    low = scene.text.lower()
    if any(x in low for x in ["father", "mother", "parents", "future", "job"]):
        return "Personal ambition or choice is challenged by family expectations."
    if any(x in low for x in ["locked", "fear", "blood", "door", "ghost", "chair"]):
        return "The character's sense of safety or control is challenged by an unsettling situation."
    if any(x in low for x in ["why", "no", "can't", "cannot", "stop", "sorry"]):
        return "Characters want or understand different things, creating interpersonal tension."
    return "Conflict is present mainly through the scene's goal, reaction, or obstacle; it may need stronger opposition if the scene feels flat."


def _analyse_scenes(scenes: list[Scene], dialogues: list[DialogueBlock]) -> list[dict[str, Any]]:
    if not scenes:
        return []
    scored = []
    for i, scene in enumerate(scenes):
        low = scene.text.lower()
        score = 0
        if i in {0, len(scenes) - 1}:
            score += 4
        score += sum(2 for w in CLIMAX_WORDS if w in low)
        score += min(scene.words / 180, 3)
        score += 1 if any(w in low for w in CONFLICT_WORDS) else 0
        scored.append((score, i, scene))
    chosen = {0, len(scenes) - 1}
    for _, i, _ in sorted(scored, reverse=True)[:MAX_SCENE_ANALYSIS]:
        chosen.add(i)
        if len(chosen) >= min(MAX_SCENE_ANALYSIS, len(scenes)):
            break

    out = []
    median_words = statistics.median([max(1, s.words) for s in scenes])
    for i in sorted(chosen):
        scene = scenes[i]
        ds = _scene_dialogues(scene, dialogues)
        chars = list(dict.fromkeys(d.character for d in ds))[:6]
        low = scene.text.lower()
        importance = "High" if i in {0, len(scenes) - 1} or any(w in low for w in CLIMAX_WORDS) else "Medium"
        if scene.words < max(18, median_words * 0.35) and importance != "High":
            importance = "Low"
        what_works = "The scene has a clear heading and contains visible action or reaction." if _is_scene_heading(scene.heading) else "The scene contains a readable story event even though standard formatting is limited."
        if chars:
            what_works += f" It gives {', '.join(chars[:3])} an active presence."
        problem = "No major pacing problem detected in this scene by the free engine."
        suggestion = "Keep the scene focused on one meaningful change in information, emotion, conflict, or direction."
        if scene.words > median_words * 1.8 and scene.words > 130:
            problem = "This scene is much longer than the script's typical scene length."
            suggestion = "Check whether repeated dialogue or action can be tightened after the scene's main purpose is achieved."
        elif scene.words < 20 and i not in {0, len(scenes) - 1}:
            problem = "This scene is very brief compared with the rest of the script."
            suggestion = "Confirm that the scene creates a clear change; otherwise consider combining it with a neighbouring scene."
        out.append({
            "scene_number": str(scene.number), "heading": scene.heading, "purpose": _scene_purpose(scene, i, len(scenes)),
            "characters": chars, "conflict": _scene_conflict(scene), "importance": importance,
            "what_works": what_works, "problem": problem, "suggestion": suggestion,
        })
    return out


def _segment_pacing(scenes: list[Scene], dialogue_metrics: dict[str, float]) -> dict[str, Any]:
    if not scenes:
        return {"overall": "Balanced", "beginning": "Unclear", "middle": "Unclear", "climax": "Unclear", "ending": "Unclear", "slow_sections": [], "rushed_sections": [], "explanation": "Not enough scene information for reliable pacing analysis."}
    lengths = [max(1, s.words) for s in scenes]
    median = statistics.median(lengths)
    slow = [s for s in scenes if s.words > max(140, median * 1.65)]
    rushed = [s for s in scenes if 0 < s.words < max(18, median * 0.35)]
    long_ratio = dialogue_metrics.get("long_ratio", 0.0)
    if long_ratio > 0.30 or len(slow) > max(2, len(scenes) * 0.35):
        overall = "Slow"
    elif len(rushed) > max(2, len(scenes) * 0.45):
        overall = "Rushed"
    elif slow or rushed:
        overall = "Mostly Balanced"
    else:
        overall = "Balanced"

    def quarter_label(start: float, end: float) -> str:
        a = math.floor(len(scenes) * start)
        b = max(a + 1, math.ceil(len(scenes) * end))
        part = scenes[a:b]
        if not part:
            return "Balanced"
        avg = statistics.mean(max(1, s.words) for s in part)
        if avg > median * 1.45 and avg > 80:
            return "Slow"
        if avg < median * 0.55 and median > 35:
            return "Rushed"
        return "Balanced"

    return {
        "overall": overall,
        "beginning": quarter_label(0.0, 0.25),
        "middle": quarter_label(0.25, 0.65),
        "climax": quarter_label(0.65, 0.88),
        "ending": quarter_label(0.88, 1.0),
        "slow_sections": [f"Scene {s.number}: {s.heading} ({s.words} words)" for s in slow[:5]],
        "rushed_sections": [f"Scene {s.number}: {s.heading} ({s.words} words)" for s in rushed[:5]],
        "explanation": f"Free mode compares scene lengths and dialogue density inside this screenplay. Typical scene length is about {median:.0f} words; this is a relative pacing signal, not a timing measurement.",
    }


def _distinctive_tokens(text: str) -> list[str]:
    words = re.findall(r"\b[A-Za-z][A-Za-z'-]{3,}\b", text.lower())
    counts = Counter(w for w in words if w not in STOPWORDS)
    return [w for w, c in counts.most_common(12) if c >= 2][:5]


def _analyse_originality(text: str, genre: str, locations: list[str], main: str) -> dict[str, Any]:
    tokens = _distinctive_tokens(text)
    score = 68
    if len(tokens) >= 3:
        score += 5
    if len(locations) >= 3:
        score += 3
    if any(x in text.lower() for x in ["film", "camera", "script", "story", "directing"]) and any(x in text.lower() for x in ["real life", "memory", "footage", "own life"]):
        score += 6
    if any(x in text.lower() for x in ["chair", "door", "photograph", "notebook", "camera"]) and any(text.lower().count(x) >= 2 for x in ["chair", "door", "photograph", "notebook", "camera"]):
        score += 4
    score = min(86, score)
    familiar = []
    if "Romance" in genre:
        familiar.append("A developing attraction or relationship is a familiar dramatic foundation.")
    if "Coming" in genre or "Drama" in genre:
        familiar.append("Young-adult identity, career, family, or friendship pressure is a familiar coming-of-age foundation.")
    if "Horror" in genre or "Thriller" in genre or "Mystery" in genre:
        familiar.append("An isolated character facing unexplained danger is a familiar suspense foundation.")
    if not familiar:
        familiar.append(f"The main {genre.lower()} setup uses recognisable genre conventions.")
    distinctive = []
    if tokens:
        distinctive.append("Recurring script-specific details detected: " + ", ".join(tokens[:4]) + ".")
    if locations:
        distinctive.append("The setting combination gives the script its own practical identity: " + ", ".join(locations[:3]) + ".")
    if main:
        distinctive.append(f"The execution is anchored around {main}'s specific choices and reactions rather than premise alone.")
    return {
        "score": score,
        "explanation": "Free mode estimates distinctiveness only from patterns inside the uploaded screenplay. It does not search the internet or compare against a database, so this is not a plagiarism or 'never done before' score.",
        "familiar_elements": familiar[:3],
        "distinctive_elements": distinctive[:3],
    }


def _analyse_show_vs_tell(lines: list[str], dialogues: list[DialogueBlock]) -> dict[str, Any]:
    cue_indices = {d.line_index for d in dialogues}
    strong = []
    for i, line in enumerate(lines):
        s = line.strip()
        if not s or META_RE.match(s) or _is_scene_heading(s) or i in cue_indices:
            continue
        low = s.lower()
        if len(s.split()) <= 28 and any(re.search(rf"\b{re.escape(v)}\b", low) for v in VISUAL_VERBS):
            strong.append(_clip(s, 135))
        if len(strong) >= 5:
            break

    telling = []
    for d in dialogues:
        low = d.text.lower()
        marker = next((m for m in TELLING_MARKERS if m in low), None)
        if marker:
            telling.append({
                "example": _clip(d.text, 125),
                "why": "The line directly explains emotion, intention, or background information that may partly be expressible through behaviour or conflict.",
                "suggestion": "Keep the essential information, but test whether an action, silence, reaction, prop, or shorter line can communicate part of it visually."
            })
        if len(telling) >= 5:
            break
    return {"strong_visual_moments": strong, "telling_moments": telling}


def _format_check(lines: list[str], scenes: list[Scene], dialogues: list[DialogueBlock]) -> dict[str, Any]:
    nonempty = [x.strip() for x in lines if x.strip()]
    scene_heads = [x for x in nonempty if _is_scene_heading(x)]
    colon_dialogue = [x for x in nonempty if re.match(r"^[A-Z][A-Za-z ]{1,25}:\s+\S", x)]
    bracket_action = [x for x in nonempty if x.startswith("(") and x.endswith(")") and len(x.split()) > 6]
    camera = [x for x in nonempty if any(k in x.upper() for k in ["CLOSE UP", "WIDE SHOT", "CAMERA", "PAN TO", "ZOOM"])]
    issues = []
    strengths = []

    if scene_heads:
        strengths.append(f"{len(scene_heads)} standard-looking scene heading(s) were detected.")
    else:
        issues.append({"type": "Scene headings", "example": "", "correction": "INT. LOCATION – DAY", "explanation": "No standard INT./EXT. scene headings were detected."})
    if dialogues:
        strengths.append("Character cue + dialogue patterns are readable to the analyser.")
    else:
        issues.append({"type": "Character cues / dialogue", "example": colon_dialogue[0] if colon_dialogue else "", "correction": "CHARACTER NAME on its own line, with dialogue below it.", "explanation": "Dialogue could not be reliably separated from action."})
    if colon_dialogue:
        issues.append({"type": "Colon dialogue", "example": _clip(colon_dialogue[0], 100), "correction": "VIJAY\nWhere is everyone?", "explanation": "Professional screenplay format usually places the character cue separately rather than writing NAME: dialogue."})
    if bracket_action:
        issues.append({"type": "Action in brackets", "example": _clip(bracket_action[0], 100), "correction": "Write physical action as a normal action paragraph.", "explanation": "Long bracketed action can make dialogue/action separation harder to read."})
    if len(camera) > max(4, len(scene_heads)):
        issues.append({"type": "Camera directions", "example": _clip(camera[0], 100), "correction": "Describe the important visual result unless the shot instruction is essential.", "explanation": "Frequent camera directions can make a student screenplay harder to read and can distract from dramatic action."})

    if not issues and scene_heads and dialogues:
        status = "Good"
    elif len(issues) <= 1 and (scene_heads or dialogues):
        status = "Mostly Good"
    elif scene_heads or dialogues:
        status = "Learning Stage"
    else:
        status = "Needs Improvement"
    return {
        "status": status,
        "affects_overall_score": False,
        "strengths": strengths,
        "issues": issues[:6],
        "confidence_note": "Formatting is assessed separately and never reduces the creative score. If formatting is unclear, free-mode extraction may be less accurate.",
    }


def _score_engine(
    scenes: list[Scene], characters: Counter, structure: dict[str, Any], dialogue_metrics: dict[str, float],
    pacing: dict[str, Any], originality: dict[str, Any], show_tell: dict[str, Any], text: str
) -> dict[str, int]:
    # Story: internal indicators only; no formatting component.
    story = 62
    if len(scenes) >= 2:
        story += 6
    if any(w in text.lower() for w in CONFLICT_WORDS):
        story += 8
    if any(w in text.lower() for w in CLIMAX_WORDS):
        story += 6
    if len(show_tell.get("strong_visual_moments", [])) >= 2:
        story += 4
    story = min(92, story)

    beat_scores = {"Clear": 1.0, "Present": 0.82, "Weak": 0.55, "Unclear": 0.45, "Missing": 0.2}
    vals = [beat_scores.get(b.get("status"), 0.5) for b in structure.get("beats", [])]
    structure_score = round(55 + (statistics.mean(vals) if vals else 0.45) * 35)

    char_score = 58
    if len(characters) >= 1:
        char_score += 8
    if len(characters) >= 2:
        char_score += 5
    if sum(characters.values()) >= 8:
        char_score += 5
    if characters and characters.most_common(1)[0][1] >= 3:
        char_score += 6
    char_score = min(90, char_score)

    dialogue_score = 84
    dialogue_score -= round(dialogue_metrics.get("long_ratio", 0) * 28)
    dialogue_score -= round(dialogue_metrics.get("expo_ratio", 0) * 22)
    dialogue_score -= round(dialogue_metrics.get("repeat_ratio", 0) * 18)
    if dialogue_metrics.get("avg_words", 0) == 0:
        dialogue_score = 55
    dialogue_score = max(45, min(92, dialogue_score))

    pacing_map = {"Balanced": 84, "Mostly Balanced": 77, "Slow": 64, "Rushed": 64}
    pacing_score = pacing_map.get(pacing.get("overall"), 72)

    originality_score = int(originality.get("score", 70))
    scores = {
        "story": int(story), "structure": int(structure_score), "characters": int(char_score),
        "dialogue": int(dialogue_score), "pacing": int(pacing_score), "originality": int(originality_score),
    }
    scores["overall"] = round(sum(scores.values()) / 6)
    return scores


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
    data.setdefault("screenplay_format", {})["affects_overall_score"] = False
    return data


def _strengths_weaknesses(scores: dict[str, int], format_data: dict[str, Any], structure: dict[str, Any], dialogue: dict[str, Any], show_tell: dict[str, Any]) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    category_names = {
        "story": "Story foundation", "structure": "Story structure", "characters": "Character presence",
        "dialogue": "Dialogue", "pacing": "Pacing", "originality": "Distinctive execution"
    }
    ranked = sorted(((v, k) for k, v in scores.items() if k != "overall"), reverse=True)
    strengths = []
    for v, k in ranked[:3]:
        strengths.append({"title": category_names[k], "explanation": f"Free-mode indicators place this area at {v}/100, making it one of the script's stronger current areas."})
    if show_tell.get("strong_visual_moments"):
        strengths.append({"title": "Visual storytelling", "explanation": "The script contains physical actions or reactions that communicate story information visually."})

    weaknesses = []
    for v, k in sorted((v, k) for k, v in scores.items() if k != "overall")[:3]:
        weaknesses.append({"title": category_names[k], "explanation": f"At {v}/100, this area contains the clearest opportunities for revision according to the free engine's internal checks."})
    if dialogue.get("overall_status") == "Needs Attention":
        weaknesses.append({"title": "Dialogue efficiency", "explanation": "Long, explanatory, or repetitive dialogue patterns may be slowing some scenes."})

    improvements = []
    for item in weaknesses[:3]:
        title = item["title"]
        if "Dialogue" in title:
            how = "Shorten repeated explanations and use reactions or actions between important lines."
        elif "Pacing" in title:
            how = "Review the longest and shortest scenes first, and confirm each creates a meaningful change."
        elif "Character" in title:
            how = "Clarify the protagonist's goal, why it matters personally, and what changes by the ending."
        elif "Structure" in title:
            how = "Make the turning point or major change more visible through a new decision, reveal, or consequence."
        elif "Distinctive" in title:
            how = "Strengthen script-specific details, character choices, recurring motifs, or perspective rather than trying to invent a completely new genre premise."
        else:
            how = "Clarify the central conflict and make sure the ending responds to what the protagonist has been trying to achieve."
        improvements.append({"problem": title, "why": item["explanation"], "how_to_improve": how, "example": "Revise one flagged scene first instead of rewriting the entire screenplay at once."})
    return strengths[:5], weaknesses[:5], improvements[:5]


def analyse_script(
    script_text: str,
    *,
    api_key: str = "",
    model: str = "Free Local Engine",
    script_type_hint: str = "Auto Detect",
    language_hint: str = "Auto Detect",
    title_hint: str = "",
    page_count: int | None = None,
) -> dict[str, Any]:
    """Analyse a screenplay without any paid API or external network call."""
    if not script_text or len(script_text.strip()) < 80:
        raise ValueError("The script is too short to analyse. Add more screenplay text.")

    text = script_text.strip()
    lines = text.splitlines()
    scenes = _split_scenes(lines)
    dialogues = _extract_dialogue(lines)
    char_counts = Counter(d.character for d in dialogues)
    characters = [name for name, _ in char_counts.most_common(20)]
    locations = _extract_locations(scenes)
    script_type = _detect_script_type(text, script_type_hint, page_count, scenes)
    genre, supporting_genres = _detect_genre(text)
    language = _detect_language(text, language_hint)
    title = title_hint.strip() or _meta_value(text, "TITLE") or "Untitled Screenplay"
    main = characters[0] if characters else "Main Character"
    second = characters[1] if len(characters) > 1 else ""
    problem = _infer_problem(text, genre)
    goal = _infer_goal(main, dialogues, text, genre)
    outcome = _last_story_line(lines)
    theme = _infer_theme(text, genre)
    word_count = len(re.findall(r"\b\w+[’']?\w*\b", text))
    estimated_minutes = max(1, round(word_count / 150))
    explicit_eps = _meta_value(text, "EPISODES")
    ep_count = len(re.findall(r"^EPISODE\s+", text, re.IGNORECASE | re.MULTILINE))
    if explicit_eps:
        m = re.search(r"\d+", explicit_eps)
        ep_count = int(m.group()) if m else ep_count

    overview = {
        "title": title,
        "script_type": script_type,
        "genre": genre,
        "supporting_genres": supporting_genres,
        "language": language,
        "page_count": page_count,
        "estimated_duration": f"≈ {estimated_minutes} min (rough text estimate)" if page_count is None else f"≈ {page_count} min (page-based estimate)",
        "character_count": len(characters),
        "location_count": len(locations),
        "scene_count": len(scenes),
        "episode_count": ep_count,
        "characters": characters,
        "locations": locations,
        "summary": _build_summary(main, second, locations, genre, problem, outcome),
        "theme": theme,
        "main_character": main,
        "goal": goal,
        "main_problem": problem,
        "outcome": outcome,
    }

    structure = _analyse_structure(script_type, scenes, lines)
    character_analysis = _analyse_characters(char_counts, dialogues, lines, main, problem)
    dialogue_analysis, dialogue_metrics = _analyse_dialogue(dialogues)
    scene_analysis = _analyse_scenes(scenes, dialogues)
    pacing = _segment_pacing(scenes, dialogue_metrics)
    originality = _analyse_originality(text, genre, locations, main)
    show_tell = _analyse_show_vs_tell(lines, dialogues)
    format_data = _format_check(lines, scenes, dialogues)
    scores = _score_engine(scenes, char_counts, structure, dialogue_metrics, pacing, originality, show_tell, text)
    strengths, weaknesses, improvements = _strengths_weaknesses(scores, format_data, structure, dialogue_analysis, show_tell)

    next_steps = []
    for imp in improvements[:3]:
        next_steps.append(imp["how_to_improve"])
    while len(next_steps) < 3:
        defaults = [
            "Clarify the protagonist's goal and what changes by the ending.",
            "Review dialogue for repeated explanation and replace some of it with reaction or action.",
            "Polish screenplay formatting after the story revision; formatting does not affect the creative score.",
        ]
        next_steps.append(defaults[len(next_steps)])

    data = {
        "overview": overview,
        "structure": structure,
        "characters": character_analysis,
        "dialogue": dialogue_analysis,
        "scenes": scene_analysis,
        "pacing": pacing,
        "originality": originality,
        "show_vs_tell": show_tell,
        "screenplay_format": format_data,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "improvement_suggestions": improvements,
        "scores": scores,
        "final_feedback": {
            "summary": f"CineVora Free analysed this screenplay locally with rule-based screenplay heuristics. The current creative guidance score is {scores['overall']}/100. Use the lowest-scoring areas and flagged scenes as revision priorities, not as academic grades.",
            "top_improvements": [x["how_to_improve"] for x in improvements[:3]],
            "next_steps": next_steps[:3],
        },
        "analysis_meta": {
            "model": "CineVora Free Local Engine",
            "coverage_note": "Full supplied text analysed locally. No API key, paid credits, or external model call used.",
            "privacy_note": "The analysis engine does not send screenplay text to OpenAI or another external AI API.",
        },
    }
    return _normalise_scores(data)
