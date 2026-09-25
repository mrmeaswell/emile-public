# Decisions

A log of what's settled and what's still open. When you decide an open item, move it to **Settled** with the date and the reason.

## Settled

| # | Decision | Choice | Why |
|---|---|---|---|
| S1 | Lane priority (was open #2) | **Lane 1 first**: MCP server over stdio and streamable HTTP on a bknown LXC. Lane 0 skill is generated from the same `data/`. | Serves Ren and colleagues; the skill comes free |
| S2 | QTI export (was open #3) | **Separate human-run script** (`scripts/export_quiz.py`) | Keeps the MCP server 100% read-only |
| S3 | Scenario content | **Generic for now.** Data files contain only what the v2.0 package states; gaps are marked `TODO(Ren)`. Wherever an example or use case is needed, use **MSCB only**. The MSCB file itself now carries the full bible (S8). | Avoids inventing canon |
| S4 | MCP SDK | `mcp==2.2.0` (`MCPServer`; `FastMCP` in the package skeleton was renamed in 2.x) | Current release at build time, pinned with hashes |
| S5 | Remote auth | Cloudflare Tunnel + Cloudflare Access + server bearer token (`Authorization: Bearer` or `X-API-Key`) | Defense in depth; never an open endpoint |
| S6 | Validator scope | Beyond the package skeleton: total count = 35, answer shape per type, unknown type/level, invalid JSON reported instead of crashing | Rules with a right answer belong in code |
| S7 | `check_load` counting | A term counts as "new" only in the first segment (split on Markdown headings) where it appears | Reuse later isn't new load |
| S8 | MSCB canon (was open #5) | **Story Bible v1.1** (May 7, 2026) in `data/mscb.md`, minus booth-production notes | Ren confirmed v1.1 as working canon; replace the file when a newer bible exists |
| S9 | CNT 180 in MSCB | CNT 180 students are **junior automation developers at TechServe**, working the Python on the utility VM (backup job, morning report, reconciliation) | Fits the existing layers without a third firm; marked [v1.2] in `data/mscb.md` |
| S10 | Unnamed entities | The regular customer, roaster, and competing shop stay **unnamed in canon; students name them** as exonyms of their own identity. Emile never supplies those names. | Ren, Sep 2026 |

## Open

1. **Exonym definition.** v1.0 defines an exonym as a familiar-concept bridge; elsewhere it's a student persona. Which is canonical, or are they two tools? *Both meanings are now in use: the system prompt keeps exonym **bridges** (familiar concept → technical term) and adds **student-named exonyms** of identity (S10). Confirm they're two tools under one name, or rename one.*
2. **Colleague access (Lane 2).** If other RTC faculty use Emile through Copilot Studio, whose tenant and whose identity provider gates it? Does Copilot Studio's MCP connector pass Cloudflare Access service-token headers, or do we need a custom connector?
3. **CNT 180 (Python) objective framework.** Course outcomes, PCEP, or other? Rubric scale is also unspecified. See `data/course-cnt180.md`.
4. **CNT 290 objective framework.** Not stated in the package. See `data/course-cnt290.md`.
5. **MSCB v1.2 bible.** The [v1.2] additions (S9, S10) live in `data/mscb.md`; fold them into the next Story Bible version.
6. **Copilot Studio resource/prompt support.** Verify in the tenant whether resources and prompts are consumed or only tools. Tools mirror everything either way.
7. **Canvas QTI import.** The exporter targets QTI 1.2 as Canvas imports it; confirm with a test import in a sandbox course, especially fill-in-the-blank and multiple-answer items.
