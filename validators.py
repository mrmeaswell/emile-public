"""Deterministic checks for Emile.

Judgment lives in the prompt; rules with a right answer live here. Every
function is pure (text in, dict out) so it can be tested without an MCP host.
"""

import json
import re
from typing_extensions import TypedDict  # pydantic requires this on Python < 3.12

BANNED = [
    r"\bsimply\b",
    r"\bobviously\b",
    r"\bas you (?:already )?know\b",
    r"\bthis is basic\b",
]
TYPES = {"true_false": 7, "multiple_choice": 12, "multiple_answer": 6, "fill_blank": 5, "manual": 5}
LEVELS = {"recall": 0.30, "application": 0.45, "analysis": 0.25}
LEVEL_TOLERANCE = 2
MAX_NEW_TERMS = 5


class LintHit(TypedDict):
    line: int
    phrase: str


class LoadSegment(TypedDict):
    heading: str
    count: int
    terms: list[str]
    over: bool


# "pass" is a keyword, so these use the functional TypedDict form.
LintResult = TypedDict("LintResult", {"pass": bool, "hits": list[LintHit]})
QuizResult = TypedDict("QuizResult", {"pass": bool, "counts": dict[str, int], "levels": dict[str, int], "issues": list[str]})
LoadResult = TypedDict("LoadResult", {"pass": bool, "max": int, "segments": list[LoadSegment]})

_NEGATION = re.compile(r"\bnot\b|n't\b", re.I)
_ALL_NONE = re.compile(r"\b(?:all|none) of the above\b", re.I)
_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+(.*?)\s*#*\s*$")


def lint_language(text: str) -> LintResult:
    """Flag deficit-framing phrases, with 1-based line numbers."""
    found = sorted(
        (n, m.start(), m.group(0))
        for n, line in enumerate(text.splitlines(), 1)
        for p in BANNED
        for m in re.finditer(p, line, re.I)
    )
    hits = [{"line": n, "phrase": phrase} for n, _, phrase in found]
    return {"pass": not hits, "hits": hits}


def _answer_issues(i: int, q: dict) -> list[str]:
    t, opts, ans = q.get("type"), q.get("options"), q.get("answer")
    if t == "manual":
        return []
    if t == "fill_blank":
        if not (isinstance(ans, list) and ans and all(isinstance(a, str) and a.strip() for a in ans)):
            return [f"Q{i}: fill_blank needs answer as a list of accepted strings"]
        return []
    if t == "true_false" and opts is None:
        opts = ["True", "False"]
    if not isinstance(opts, list) or not all(isinstance(o, str) for o in opts):
        return [f"Q{i}: options must be a list of strings"]
    if t == "true_false" and len(opts) != 2:
        return [f"Q{i}: true_false needs exactly 2 options"]
    if t in ("multiple_choice", "multiple_answer") and len(opts) < 3:
        return [f"Q{i}: {t} needs at least 3 options"]
    if not (isinstance(ans, list) and ans and all(isinstance(a, int) and not isinstance(a, bool) for a in ans)):
        return [f"Q{i}: answer must be a list of option indices"]
    issues = []
    if any(a < 0 or a >= len(opts) for a in ans):
        issues.append(f"Q{i}: answer index out of range")
    if len(set(ans)) != len(ans):
        issues.append(f"Q{i}: duplicate answer index")
    if t in ("true_false", "multiple_choice") and len(ans) != 1:
        issues.append(f"Q{i}: {t} needs exactly one answer")
    if t == "multiple_answer" and len(set(ans)) < 2:
        issues.append(f"Q{i}: multiple_answer needs two or more answers")
    return issues


def validate_quiz(quiz_json: str) -> QuizResult:
    """Check a quiz draft against the RTC Standard Quiz Package spec."""
    try:
        data = json.loads(quiz_json)
    except (json.JSONDecodeError, TypeError) as e:
        return {"pass": False, "counts": {}, "levels": {}, "issues": [f"invalid JSON: {e}"]}
    qs = data.get("questions") if isinstance(data, dict) else None
    if not isinstance(qs, list) or not all(isinstance(q, dict) for q in qs):
        return {"pass": False, "counts": {}, "levels": {}, "issues": ["'questions' must be a list of objects"]}

    counts = {t: sum(q.get("type") == t for q in qs) for t in TYPES}
    levels = {lv: sum(q.get("level") == lv for q in qs) for lv in LEVELS}
    total = sum(TYPES.values())

    issues = []
    if len(qs) != total:
        issues.append(f"total: {len(qs)} items (target {total})")
    issues += [f"{t}: {counts[t]} (target {n})" for t, n in TYPES.items() if counts[t] != n]
    issues += [
        f"{lv}: {levels[lv]} (target ~{round(len(qs) * r)})"
        for lv, r in LEVELS.items()
        if abs(levels[lv] - len(qs) * r) > LEVEL_TOLERANCE
    ]
    for i, q in enumerate(qs, 1):
        if q.get("type") not in TYPES:
            issues.append(f"Q{i}: unknown type {q.get('type')!r}")
        if q.get("level") not in LEVELS:
            issues.append(f"Q{i}: unknown level {q.get('level')!r}")
        if not str(q.get("objective") or "").strip():
            issues.append(f"Q{i}: no objective mapped")
        stem = q.get("stem")
        if not isinstance(stem, str) or not stem.strip():
            issues.append(f"Q{i}: missing stem")
            stem = ""
        opts = q.get("options") or []
        if isinstance(opts, list) and any(_ALL_NONE.search(str(o)) for o in opts):
            issues.append(f"Q{i}: all/none of the above")
        if len(_NEGATION.findall(stem)) >= 2:
            issues.append(f"Q{i}: possible double negative, review")
        if q.get("type") in TYPES:
            issues += _answer_issues(i, q)
    return {"pass": not issues, "counts": counts, "levels": levels, "issues": issues}


def _segments(text: str) -> list[tuple[str, str]]:
    """Split Markdown into (heading, body) segments; the body includes the heading text.

    Text before the first heading is '(intro)'.
    """
    segs, heading, buf = [], "(intro)", []
    for line in text.splitlines():
        m = _HEADING.match(line)
        if m:
            if heading != "(intro)" or any(b.strip() for b in buf):
                segs.append((heading, "\n".join(buf)))
            heading, buf = m.group(1) or "(untitled)", [m.group(1)]
        else:
            buf.append(line)
    segs.append((heading, "\n".join(buf)))
    return segs


def check_load(text: str, new_terms: list[str]) -> LoadResult:
    """Flag segments that introduce more than MAX_NEW_TERMS of the given new terms.

    A term counts in the first segment where it appears (that is where it is
    introduced); later mentions are reuse, not new load.
    """
    terms = [t.strip() for t in dict.fromkeys(new_terms) if t and t.strip()]
    seen: set[str] = set()
    out = []
    for heading, body in _segments(text):
        found = [
            t for t in terms
            if t.lower() not in seen and re.search(rf"(?<!\w){re.escape(t)}(?!\w)", body, re.I)
        ]
        seen.update(t.lower() for t in found)
        out.append({"heading": heading, "count": len(found), "terms": found, "over": len(found) > MAX_NEW_TERMS})
    return {"pass": not any(s["over"] for s in out), "max": MAX_NEW_TERMS, "segments": out}
