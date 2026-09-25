# RTC Standard Quiz Package — Specification

A quiz package is **35 items**. Every rule below marked **[checked]** is enforced by `emile_validate_quiz`; the rest are judgment calls for the model and the instructor.

## Item types [checked]

| Type | JSON `type` | Count |
|---|---|---|
| True/False | `true_false` | 7 |
| Multiple choice (one correct) | `multiple_choice` | 12 |
| Multiple answer (two or more correct) | `multiple_answer` | 6 |
| Fill in the blank | `fill_blank` | 5 |
| Manually graded (short answer / essay) | `manual` | 5 |

## Difficulty mix [checked, ±2 items per level]

| Level | JSON `level` | Share | Items (of 35) |
|---|---|---|---|
| Recall | `recall` | 30% | ~10 |
| Application | `application` | 45% | ~16 |
| Analysis | `analysis` | 25% | ~9 |

## Item rules

- **[checked]** Every item maps to an objective (`objective` is non-empty). Use the course's objective framework (see `emile://course/{code}`).
- **[checked]** No "all of the above" or "none of the above."
- **[checked]** No double negatives (two or more "not"/"n't" in a stem is flagged for review).
- **[checked]** Answer shape matches type (see the contract below).
- No trick items. A wrong answer should tell the instructor *what* the learner misunderstood.
- Distractors are plausible and instructive; the `rationale` explains why the answer is right and what each distractor reveals.
- Items are scenario-anchored where it helps. When a scenario is used, use the MSCB universe (`emile://scenario/mscb`).
- The Analogy Bridge is **off** for quiz items.

## Quiz JSON contract

The host model drafts to this shape. A separate, human-run step (`scripts/export_quiz.py`) converts it to Canvas QTI and Word.

```json
{
  "course": "CNT160",
  "title": "Module 3 — Windows Security",
  "questions": [
    {
      "type": "multiple_choice",
      "level": "application",
      "objective": "220-1202 2.1",
      "stem": "Maya at Main Street Coffee & Books reports...",
      "options": ["...", "...", "...", "..."],
      "answer": [1],
      "rationale": "Why the answer is right and each distractor is instructive"
    }
  ]
}
```

### `answer` by type [checked]

| Type | `options` | `answer` |
|---|---|---|
| `true_false` | `["True", "False"]` (may be omitted) | one index: `[0]` = True, `[1]` = False |
| `multiple_choice` | 3+ strings | exactly one index |
| `multiple_answer` | 3+ strings | two or more indices |
| `fill_blank` | omitted | one or more accepted strings, e.g. `["NTFS"]` |
| `manual` | omitted | omitted; put grading notes in `rationale` |

Indices are zero-based.
