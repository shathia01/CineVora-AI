from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _register_unicode_font() -> str:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            try:
                pdfmetrics.registerFont(TTFont("CineVoraFont", path))
                return "CineVoraFont"
            except Exception:
                pass
    return "Helvetica"


def _safe(value: Any) -> str:
    if value is None:
        return "—"
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_pdf_report(data: dict[str, Any]) -> bytes:
    buffer = BytesIO()
    font = _register_unicode_font()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=16*mm, leftMargin=16*mm, topMargin=16*mm, bottomMargin=16*mm)
    styles = getSampleStyleSheet()
    title = ParagraphStyle("CVTitle", parent=styles["Title"], fontName=font, fontSize=24, leading=28, textColor=colors.HexColor("#191919"), spaceAfter=10)
    h1 = ParagraphStyle("CVH1", parent=styles["Heading1"], fontName=font, fontSize=15, leading=18, spaceBefore=10, spaceAfter=6)
    h2 = ParagraphStyle("CVH2", parent=styles["Heading2"], fontName=font, fontSize=11.5, leading=14, spaceBefore=7, spaceAfter=3)
    body = ParagraphStyle("CVBody", parent=styles["BodyText"], fontName=font, fontSize=9.3, leading=13, spaceAfter=5)
    small = ParagraphStyle("CVSmall", parent=body, fontSize=8.2, textColor=colors.HexColor("#555555"))

    story = [Paragraph("CineVora AI — Student Script Report", title)]
    ov = data.get("overview", {})
    story.append(Paragraph(_safe(ov.get("title") or "Untitled Screenplay"), h1))
    meta = [
        ["Type", ov.get("script_type", "—"), "Genre", ov.get("genre", "—")],
        ["Language", ov.get("language", "—"), "Duration", ov.get("estimated_duration", "—")],
        ["Pages", ov.get("page_count", "—"), "Overall Score", f"{data.get('scores', {}).get('overall', 0)}/100"],
    ]
    table = Table(meta, colWidths=[24*mm, 55*mm, 28*mm, 55*mm])
    table.setStyle(TableStyle([
        ("FONTNAME", (0,0), (-1,-1), font), ("FONTSIZE", (0,0), (-1,-1), 8.8),
        ("BACKGROUND", (0,0), (0,-1), colors.HexColor("#F2F2F2")),
        ("BACKGROUND", (2,0), (2,-1), colors.HexColor("#F2F2F2")),
        ("GRID", (0,0), (-1,-1), 0.25, colors.HexColor("#D5D5D5")),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 5), ("RIGHTPADDING", (0,0), (-1,-1), 5),
        ("TOPPADDING", (0,0), (-1,-1), 5), ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ]))
    story += [table, Spacer(1, 8), Paragraph("Script Overview", h1), Paragraph(_safe(ov.get("summary")), body), Paragraph(f"<b>Main Theme:</b> {_safe(ov.get('theme'))}", body)]

    scores = data.get("scores", {})
    story.append(Paragraph("Creative Score", h1))
    score_rows = [[k.title(), scores.get(k, 0)] for k in ["story", "structure", "characters", "dialogue", "pacing", "originality"]]
    score_table = Table(score_rows, colWidths=[65*mm, 25*mm])
    score_table.setStyle(TableStyle([
        ("FONTNAME", (0,0), (-1,-1), font), ("FONTSIZE", (0,0), (-1,-1), 9),
        ("GRID", (0,0), (-1,-1), 0.25, colors.HexColor("#D5D5D5")),
        ("BACKGROUND", (0,0), (0,-1), colors.HexColor("#F7F7F7")),
        ("ALIGN", (1,0), (1,-1), "CENTER"),
    ]))
    story += [score_table, Paragraph("Free-mode scores are guidance, not academic grades. Screenplay formatting is assessed separately and does not affect this score.", small)]

    story.append(Paragraph("Story / Series Structure", h1))
    story.append(Paragraph(_safe(data.get("structure", {}).get("summary")), body))
    for beat in data.get("structure", {}).get("beats", []):
        story.append(Paragraph(f"<b>{_safe(beat.get('name'))} — {_safe(beat.get('status'))}</b>", h2))
        story.append(Paragraph(f"{_safe(beat.get('evidence'))}<br/><b>Feedback:</b> {_safe(beat.get('feedback'))}", body))

    story.append(PageBreak())
    story.append(Paragraph("Character Analysis", h1))
    for ch in data.get("characters", []):
        story.append(Paragraph(f"{_safe(ch.get('name'))} — {_safe(ch.get('role'))}", h2))
        story.append(Paragraph(
            f"<b>Goal:</b> {_safe(ch.get('goal'))}<br/>"
            f"<b>Motivation:</b> {_safe(ch.get('motivation'))}<br/>"
            f"<b>Conflict:</b> {_safe(ch.get('conflict'))}<br/>"
            f"<b>Development:</b> {_safe(ch.get('development'))}<br/>"
            f"<b>Arc:</b> {_safe(ch.get('arc'))}", body))

    story.append(Paragraph("Dialogue Analysis", h1))
    story.append(Paragraph(_safe(data.get("dialogue", {}).get("summary")), body))
    for finding in data.get("dialogue", {}).get("findings", []):
        story.append(Paragraph(f"{_safe(finding.get('category'))} — {_safe(finding.get('status'))}", h2))
        story.append(Paragraph(f"<b>Example:</b> {_safe(finding.get('example'))}<br/><b>Why:</b> {_safe(finding.get('why_it_matters'))}<br/><b>Suggestion:</b> {_safe(finding.get('suggestion'))}", body))

    story.append(Paragraph("Pacing", h1))
    pacing = data.get("pacing", {})
    story.append(Paragraph(f"<b>Overall:</b> {_safe(pacing.get('overall'))}<br/>{_safe(pacing.get('explanation'))}", body))

    story.append(Paragraph("Originality", h1))
    originality = data.get("originality", {})
    story.append(Paragraph(f"<b>Guidance score:</b> {_safe(originality.get('score'))}/100<br/>{_safe(originality.get('explanation'))}", body))

    story.append(Paragraph("Show vs Tell", h1))
    for moment in data.get("show_vs_tell", {}).get("strong_visual_moments", []):
        story.append(Paragraph(f"• {_safe(moment)}", body))
    for item in data.get("show_vs_tell", {}).get("telling_moments", []):
        story.append(Paragraph(f"<b>Possible telling:</b> {_safe(item.get('example'))}<br/><b>Suggestion:</b> {_safe(item.get('suggestion'))}", body))

    story.append(Paragraph("Screenplay Format Check", h1))
    fmt = data.get("screenplay_format", {})
    story.append(Paragraph(f"<b>Status:</b> {_safe(fmt.get('status'))}<br/>This section does not affect the creative score.", body))
    for issue in fmt.get("issues", []):
        story.append(Paragraph(f"<b>{_safe(issue.get('type'))}</b>: {_safe(issue.get('explanation'))}<br/><b>Correction:</b> {_safe(issue.get('correction'))}", body))

    story.append(PageBreak())
    story.append(Paragraph("Final Feedback", h1))
    story.append(Paragraph(_safe(data.get("final_feedback", {}).get("summary")), body))

    story.append(Paragraph("What Works", h2))
    for item in data.get("strengths", [])[:5]:
        story.append(Paragraph(f"• <b>{_safe(item.get('title'))}</b> — {_safe(item.get('explanation'))}", body))

    story.append(Paragraph("Needs Improvement", h2))
    for item in data.get("weaknesses", [])[:5]:
        story.append(Paragraph(f"• <b>{_safe(item.get('title'))}</b> — {_safe(item.get('explanation'))}", body))

    story.append(Paragraph("Top 3 Next Steps", h2))
    labels = ["Fix First", "Fix Next", "Polish Last"]
    for i, step in enumerate(data.get("final_feedback", {}).get("next_steps", [])[:3]):
        story.append(Paragraph(f"<b>{labels[i] if i < len(labels) else f'Priority {i+1}'}:</b> {_safe(step)}", body))

    doc.build(story)
    return buffer.getvalue()
