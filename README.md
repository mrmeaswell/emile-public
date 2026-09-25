# Emile

**An instructor-facing curriculum collaborator, packaged as a portable agent.**
Emile (Émile Durkheim × MF DOOM) co-designs modules, quizzes, labs, and instructor guides with instructors, and pushes back when work drifts from sound pedagogy. It is part of Pocket Pedagogy by Ren Tarvin, Blended Knowledge LLC.

This repository holds:

- a **system prompt** that any capable model can adopt, and
- a thin **MCP server** that serves Emile's specs and scenario and runs **deterministic checks** on drafts.

> Emile works with **instructors only**. Don't send it student names, grades, or submissions (FERPA). It never writes to Canvas; a human publishes.

## The core idea: judgment in the prompt, rules in code

> **The LLM may shape what the instructor reads. It may never be the only thing checking the rules.**

**Analogy:** the MCP server is a **music library plus a tuner**. Any musician (Claude, Copilot, a local model) can pick up the sheet music (the prompt) and play Emile. The tuner (the validators) doesn't care who played. It only reports whether each note is in pitch.

| Needs judgment → the **model** | Has a right answer → **code** |
|---|---|
| Is this analogy good? | Does the quiz have 7 TF / 12 MC / 6 MA / 5 FIB / 5 manual? |
| Is the lab's arc right? | Does any item use "all of the above"? |
| Should this segment be split? | Does the text say "simply" or "obviously"? |

## What the server exposes

It is a **thin server**: it never calls an LLM, stores no API keys, and makes no outbound network calls. Every tool is read-only.

| Kind | Name | What it does |
|---|---|---|
| Prompt | `emile` (`task`, optional `course`) | System prompt + course context + your task |
| Resource / tool | `emile://spec/quiz-package` / `emile_get_quiz_spec` | RTC Standard Quiz Package spec and quiz JSON contract |
| Resource / tool | `emile://scenario/mscb` / `emile_get_scenario` | Main Street Coffee & Books story bible summary |
| Resource / tool | `emile://course/{code}` / `emile_get_course_context` | Course title, objective framework, rubric scale, provider |
| Resource / tool | `emile://antipatterns` / `emile_get_antipatterns` | The 11 anti-patterns |
| Validator | `emile_lint_language` | Flags deficit framing, by line |
| Validator | `emile_validate_quiz` | Type counts, 30/45/25 difficulty mix (±2), objectives, all/none of the above, double negatives, answer shape |
| Validator | `emile_check_load` | Flags any segment that introduces more than 5 new terms |

Every resource is mirrored as a tool because some hosts, such as Copilot Studio, only consume tools.

## Quick start (local, stdio)

```bash
git clone https://github.com/mrmeaswell/emile-public.git emile && cd emile
python3 -m venv .venv && . .venv/bin/activate
pip install --require-hashes -r requirements.txt
python server.py            # speaks MCP over stdio
```

**Claude Code** — add to `.mcp.json` in your project:

```json
{
  "mcpServers": {
    "emile": { "command": "/path/to/emile/.venv/bin/python", "args": ["/path/to/emile/server.py"] }
  }
}
```

**Claude Code against the remote server** (after [DEPLOY.md](DEPLOY.md)):

```json
{
  "mcpServers": {
    "emile": {
      "type": "http",
      "url": "https://emile.example.com/mcp",
      "headers": { "Authorization": "Bearer ${EMILE_TOKEN}" }
    }
  }
}
```

Then allow only the read tools, e.g. `"permissions": {"allow": ["mcp__emile__emile_*"]}` in `.claude/settings.json`.

## Three ways to ship the same Emile

The content in `data/` is plain Markdown, so the same core ships three ways:

| Lane | Host | How |
|---|---|---|
| 0. Claude Skill | Claude.ai / Claude Code | [`skill/emile/SKILL.md`](skill/emile/SKILL.md), generated from `data/` |
| 1. MCP server | Claude Code, Claude Desktop, any MCP client | `python server.py` (stdio) or the remote HTTP server |
| 2. Copilot Studio | Microsoft 365 | Paste `data/emile-system.md` into the agent's instructions; add the remote server as an MCP tool source (`X-API-Key` header auth) |

## Exporting a quiz to Canvas and Word

Export is a **human-run** step, kept outside the server so the server stays read-only:

```bash
pip install --require-hashes -r requirements-export.txt   # only needed for Word
python scripts/export_quiz.py my-quiz.json                # -> my-quiz.qti.zip + my-quiz.docx
```

The script refuses to export a quiz that fails validation. `--force` overrides spec rules such as counts, but it still refuses items it can't render. In Canvas, import the `.zip` via **Settings → Import Course Content → QTI .zip file**. Try it in a sandbox course first.

[`examples/sample-quiz.json`](examples/sample-quiz.json) shows one item of each type in the MSCB scenario. It fails the 35-item count on purpose, so you can see the validator's output.

## Repository layout

```
server.py                 MCP server: prompt, resources, tools, token-gated HTTP
validators.py             pure deterministic checks (no MCP dependency)
data/                     single source of truth: system prompt, spec, scenario, courses
skill/emile/SKILL.md      Lane 0 skill (generated: python scripts/build_skill.py)
scripts/export_quiz.py    quiz JSON -> Canvas QTI 1.2 zip + Word
deploy/                   systemd unit, install script, env + cloudflared examples
tests/                    validator, server, HTTP-auth, and export tests
DEPLOY.md                 remote server (Proxmox LXC + Cloudflare Tunnel) guide
DECISIONS.md              open and settled design decisions
```

## Development

```bash
pip install --require-hashes -r requirements-dev.txt
python -m pytest -q
python scripts/build_skill.py          # after editing anything in data/
```

Dependencies are pinned with hashes (`requirements*.txt`, compiled from `requirements*.in` with `pip-compile --generate-hashes`). To upgrade, edit the `.in` file and recompile.

## Editing Emile's content

Edit files in `data/`, then regenerate the skill. Lines marked `TODO(Ren)` are gaps the source package didn't specify, such as CNT 180's objective framework. See [DECISIONS.md](DECISIONS.md).

---

*Emile is a living document. It evolves as the methodology evolves.*
*Pocket Pedagogy is the work of Ren Tarvin, Blended Knowledge LLC.*

## Copyright

Copyright (c) 2026 Blended Knowledge LLC. All rights reserved. No license is granted; see `CITATION.cff` to cite this work.
