from __future__ import annotations


def _string_array():
    return {"type": "array", "items": {"type": "string"}}


def analysis_schema() -> dict:
    score_props = {
        key: {"type": "integer", "minimum": 0, "maximum": 100}
        for key in ["story", "structure", "characters", "dialogue", "pacing", "originality", "overall"]
    }

    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "overview": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "title": {"type": "string"},
                    "script_type": {"type": "string", "enum": ["Short Film", "Feature Film", "Web Series", "Pilot", "Unknown"]},
                    "genre": {"type": "string"},
                    "supporting_genres": _string_array(),
                    "language": {"type": "string"},
                    "page_count": {"type": ["integer", "null"]},
                    "estimated_duration": {"type": "string"},
                    "character_count": {"type": "integer", "minimum": 0},
                    "location_count": {"type": "integer", "minimum": 0},
                    "scene_count": {"type": "integer", "minimum": 0},
                    "episode_count": {"type": "integer", "minimum": 0},
                    "characters": _string_array(),
                    "locations": _string_array(),
                    "summary": {"type": "string"},
                    "theme": {"type": "string"},
                    "main_character": {"type": "string"},
                    "goal": {"type": "string"},
                    "main_problem": {"type": "string"},
                    "outcome": {"type": "string"},
                },
                "required": ["title", "script_type", "genre", "supporting_genres", "language", "page_count", "estimated_duration", "character_count", "location_count", "scene_count", "episode_count", "characters", "locations", "summary", "theme", "main_character", "goal", "main_problem", "outcome"],
            },
            "structure": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "overall_status": {"type": "string"},
                    "summary": {"type": "string"},
                    "beats": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "name": {"type": "string"},
                                "status": {"type": "string", "enum": ["Clear", "Present", "Weak", "Unclear", "Missing"]},
                                "evidence": {"type": "string"},
                                "feedback": {"type": "string"},
                            },
                            "required": ["name", "status", "evidence", "feedback"],
                        },
                    },
                    "episodes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "episode": {"type": "string"},
                                "opening": {"type": "string"},
                                "main_event": {"type": "string"},
                                "conflict": {"type": "string"},
                                "character_development": {"type": "string"},
                                "ending_hook": {"type": "string"},
                            },
                            "required": ["episode", "opening", "main_event", "conflict", "character_development", "ending_hook"],
                        },
                    },
                },
                "required": ["overall_status", "summary", "beats", "episodes"],
            },
            "characters": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "name": {"type": "string"},
                        "role": {"type": "string"},
                        "goal": {"type": "string"},
                        "motivation": {"type": "string"},
                        "conflict": {"type": "string"},
                        "strength": {"type": "string"},
                        "weakness": {"type": "string"},
                        "development": {"type": "string"},
                        "arc": {"type": "string"},
                    },
                    "required": ["name", "role", "goal", "motivation", "conflict", "strength", "weakness", "development", "arc"],
                },
            },
            "dialogue": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "overall_status": {"type": "string"},
                    "summary": {"type": "string"},
                    "findings": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "category": {"type": "string", "enum": ["Natural", "Long", "Unnecessary", "Repetitive", "Too Much Exposition", "Character Voice"]},
                                "status": {"type": "string", "enum": ["Good", "Needs Attention"]},
                                "example": {"type": "string"},
                                "problem": {"type": "string"},
                                "why_it_matters": {"type": "string"},
                                "suggestion": {"type": "string"},
                            },
                            "required": ["category", "status", "example", "problem", "why_it_matters", "suggestion"],
                        },
                    },
                },
                "required": ["overall_status", "summary", "findings"],
            },
            "scenes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "scene_number": {"type": "string"},
                        "heading": {"type": "string"},
                        "purpose": {"type": "string"},
                        "characters": _string_array(),
                        "conflict": {"type": "string"},
                        "importance": {"type": "string", "enum": ["Low", "Medium", "High"]},
                        "what_works": {"type": "string"},
                        "problem": {"type": "string"},
                        "suggestion": {"type": "string"},
                    },
                    "required": ["scene_number", "heading", "purpose", "characters", "conflict", "importance", "what_works", "problem", "suggestion"],
                },
            },
            "pacing": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "overall": {"type": "string", "enum": ["Slow", "Balanced", "Rushed", "Mostly Balanced"]},
                    "beginning": {"type": "string"},
                    "middle": {"type": "string"},
                    "climax": {"type": "string"},
                    "ending": {"type": "string"},
                    "slow_sections": _string_array(),
                    "rushed_sections": _string_array(),
                    "explanation": {"type": "string"},
                },
                "required": ["overall", "beginning", "middle", "climax", "ending", "slow_sections", "rushed_sections", "explanation"],
            },
            "originality": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "score": {"type": "integer", "minimum": 0, "maximum": 100},
                    "explanation": {"type": "string"},
                    "familiar_elements": _string_array(),
                    "distinctive_elements": _string_array(),
                },
                "required": ["score", "explanation", "familiar_elements", "distinctive_elements"],
            },
            "show_vs_tell": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "strong_visual_moments": _string_array(),
                    "telling_moments": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "example": {"type": "string"},
                                "why": {"type": "string"},
                                "suggestion": {"type": "string"},
                            },
                            "required": ["example", "why", "suggestion"],
                        },
                    },
                },
                "required": ["strong_visual_moments", "telling_moments"],
            },
            "screenplay_format": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "status": {"type": "string", "enum": ["Good", "Mostly Good", "Learning Stage", "Needs Improvement"]},
                    "affects_overall_score": {"type": "boolean"},
                    "strengths": _string_array(),
                    "issues": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "type": {"type": "string"},
                                "example": {"type": "string"},
                                "correction": {"type": "string"},
                                "explanation": {"type": "string"},
                            },
                            "required": ["type", "example", "correction", "explanation"],
                        },
                    },
                    "confidence_note": {"type": "string"},
                },
                "required": ["status", "affects_overall_score", "strengths", "issues", "confidence_note"],
            },
            "strengths": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {"title": {"type": "string"}, "explanation": {"type": "string"}},
                    "required": ["title", "explanation"],
                },
            },
            "weaknesses": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {"title": {"type": "string"}, "explanation": {"type": "string"}},
                    "required": ["title", "explanation"],
                },
            },
            "improvement_suggestions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "problem": {"type": "string"},
                        "why": {"type": "string"},
                        "how_to_improve": {"type": "string"},
                        "example": {"type": "string"},
                    },
                    "required": ["problem", "why", "how_to_improve", "example"],
                },
            },
            "scores": {
                "type": "object",
                "additionalProperties": False,
                "properties": score_props,
                "required": list(score_props.keys()),
            },
            "final_feedback": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "summary": {"type": "string"},
                    "top_improvements": _string_array(),
                    "next_steps": _string_array(),
                },
                "required": ["summary", "top_improvements", "next_steps"],
            },
        },
        "required": ["overview", "structure", "characters", "dialogue", "scenes", "pacing", "originality", "show_vs_tell", "screenplay_format", "strengths", "weaknesses", "improvement_suggestions", "scores", "final_feedback"],
    }
