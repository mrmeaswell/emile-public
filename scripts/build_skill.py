#!/usr/bin/env python3
"""Build the Lane 0 Claude Skill (skill/emile/SKILL.md) from data/.

data/ is the single source of truth; never edit SKILL.md by hand. Re-run this
after changing anything in data/ (a test fails if you forget).

    python scripts/build_skill.py           # write skill/emile/SKILL.md
    python scripts/build_skill.py --check   # exit 1 if it is out of date
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "skill" / "emile" / "SKILL.md"

FRONTMATTER = """\
---
name: emile
description: Emile, an instructor-facing curriculum collaborator (Pocket Pedagogy). Use when designing or reviewing course modules, quizzes, labs, instructor guides, or Canvas pages, especially quiz packages that must follow the RTC Standard Quiz Package spec. Instructor-facing only; never for student data.
---
"""

LANE0_NOTE = """\
> **Generated from `data/` by `scripts/build_skill.py`. Do not edit by hand.**
>
> **Checks in this lane:** if the `emile` MCP server is connected, call its `emile_*` tools as the
> system prompt says. If it is not, you cannot run the validators: check the rules in the quiz
> spec and anti-patterns sections yourself, and tell the instructor the checks were done by
> the model, not by code.
"""


def build() -> str:
    sections = [
        FRONTMATTER,
        LANE0_NOTE,
        (DATA / "emile-system.md").read_text(encoding="utf-8"),
        (DATA / "quiz-package.md").read_text(encoding="utf-8"),
        (DATA / "mscb.md").read_text(encoding="utf-8"),
        (DATA / "antipatterns.md").read_text(encoding="utf-8"),
        *(p.read_text(encoding="utf-8") for p in sorted(DATA.glob("course-*.md"))),
    ]
    return "\n\n".join(s.strip() for s in sections) + "\n"


def main() -> None:
    content = build()
    if "--check" in sys.argv:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != content:
            sys.exit("skill/emile/SKILL.md is out of date; run: python scripts/build_skill.py")
        return
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(content, encoding="utf-8")
    print("Wrote", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
