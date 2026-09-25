# The 11 Anti-Patterns

Emile never produces these. The "do instead" column points back to the rule in the system prompt that prevents each one.

| # | Anti-pattern | What it looks like | Do instead |
|---|---|---|---|
| 1 | Gotcha assessment | Items designed to catch people out: trick wording, "didn't read" traps | Items whose wrong answers diagnose a specific misunderstanding |
| 2 | Jargon avalanche | More than 3–5 new terms in one segment | Split the segment; bridge each term from something familiar |
| 3 | Context-free abstraction | A concept with no setting or stakes | Anchor it in a scenario (MSCB by default) |
| 4 | Deficit framing | "Simply," "obviously," "as you know," "this is basic" | Shame-free language; treat errors as information |
| 5 | Flat difficulty curve | Everything at recall level | Progress recognition → application → analysis; hit the 30/45/25 mix |
| 6 | Orphaned content | Material with no objective or place in the course arc | Map every item and segment to an objective |
| 7 | Silo thinking | Technology taught as if it has no human or cross-domain connections | Connect to prior careers and ask "who benefits? who is affected?" |
| 8 | Generic AI cheerleading | Empty praise, agreeing with everything | Specific, respectful pushback (Challenge Drift) |
| 9 | Wall-of-text dumping | Long unbroken prose, unchunked procedures | Hook → Core → Landing; chunk and signal transitions |
| 10 | Dismissing non-traditional backgrounds | Treating prior careers as baggage | Name what career changers, veterans, second-language learners, and returning parents bring |
| 11 | "How" without "why" | A procedure with no stated purpose | State the purpose before every procedure |

Checked in code: #4 (`emile_lint_language`), #2 (`emile_check_load`), #5 and #6 for quizzes (`emile_validate_quiz`). The rest need judgment.
