from pathlib import Path

from src.parser import read_sample


def test_sample_can_be_read():
    root = Path(__file__).resolve().parents[1]
    text = read_sample(root / "samples" / "mystery_short.txt")
    assert "THE LAST STUDY ROOM" in text
    assert "INT. UNIVERSITY STUDY ROOM" in text
