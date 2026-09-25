import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

MSCB_PEOPLE = ["Maya Chen", "Ben Halvorsen", "Sarah Caldwell", "James Vasquez"]


def make_question(qtype: str, level: str, n: int) -> dict:
    who = MSCB_PEOPLE[n % len(MSCB_PEOPLE)]
    q = {
        "type": qtype,
        "level": level,
        "objective": f"220-1202 2.{n % 10 + 1}",
        "stem": f"{who} at Main Street Coffee & Books reports a problem with the register PC (item {n}).",
        "rationale": "Why the answer is right and what each distractor reveals.",
    }
    if qtype == "true_false":
        q |= {"options": ["True", "False"], "answer": [n % 2]}
    elif qtype == "multiple_choice":
        q |= {"options": ["Option A", "Option B", "Option C", "Option D"], "answer": [1]}
    elif qtype == "multiple_answer":
        q |= {"options": ["Option A", "Option B", "Option C", "Option D"], "answer": [0, 2]}
    elif qtype == "fill_blank":
        q |= {"answer": ["NTFS", "ntfs"]}
    return q


def make_valid_quiz() -> dict:
    """A 35-item quiz that satisfies the spec: 7/12/6/5/5 types and 10/16/9 levels."""
    types = ["true_false"] * 7 + ["multiple_choice"] * 12 + ["multiple_answer"] * 6 + ["fill_blank"] * 5 + ["manual"] * 5
    levels = ["recall"] * 10 + ["application"] * 16 + ["analysis"] * 9
    return {
        "course": "CNT160",
        "title": "Module 3 — Windows Security",
        "questions": [make_question(t, lv, i) for i, (t, lv) in enumerate(zip(types, levels), 1)],
    }


@pytest.fixture
def valid_quiz() -> dict:
    return make_valid_quiz()
