from src.ai_engine import _normalise_scores


def test_format_does_not_affect_overall():
    data = {
        "scores": {"story": 90, "structure": 80, "characters": 70, "dialogue": 60, "pacing": 50, "originality": 40, "overall": 1},
        "screenplay_format": {"status": "Needs Improvement", "affects_overall_score": True},
    }
    out = _normalise_scores(data)
    assert out["scores"]["overall"] == 65
    assert out["screenplay_format"]["affects_overall_score"] is False
