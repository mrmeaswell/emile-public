"""Emile MCP server: prompt + resources + deterministic validators.

Thin server: it never calls an LLM, needs no API keys, and makes no outbound
network calls. Generation happens in whichever host model loads the prompt.

    python server.py                      # stdio (Claude Code / Desktop)
    python server.py --transport http     # streamable HTTP (needs EMILE_TOKEN)
"""

import argparse
import hmac
import os
import re
import sys
from pathlib import Path

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ResourceNotFoundError, ToolError
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from starlette.responses import PlainTextResponse

import validators

DATA = Path(__file__).resolve().parent / "data"
RO = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)
DATA_NOTE = "Instructor-facing only; do not send student names, grades, or submissions (FERPA)."

mcp = MCPServer(
    "emile",
    version="2.0.0",
    instructions="Emile is an instructor-facing curriculum collaborator. " + DATA_NOTE,
)


def read(name: str) -> str:
    return (DATA / name).read_text(encoding="utf-8")


def courses() -> list[str]:
    """Course codes with a context file, e.g. ['CNT160', 'CNT180', ...]."""
    return sorted(p.stem.removeprefix("course-").upper() for p in DATA.glob("course-*.md"))


def course_file(code: str) -> str:
    """Normalize 'CNT 160' / 'cnt160' and return its file name, or raise ValueError."""
    norm = re.sub(r"[\s_-]", "", code or "").upper()
    if norm not in courses():
        raise ValueError(f"Unknown course {code!r}. Known courses: {', '.join(courses())}")
    return f"course-{norm.lower()}.md"


# --- Prompt ---------------------------------------------------------------

@mcp.prompt(description="Load Emile's system prompt, optional course context, and the task.")
def emile(task: str, course: str = "") -> str:
    parts = [read("emile-system.md"), read(course_file(course)) if course else "", f"## Task\n{task}"]
    return "\n\n".join(p.strip() for p in parts if p)


# --- Resources (each mirrored as a read-only tool for tools-only hosts) ----

@mcp.resource("emile://spec/quiz-package", mime_type="text/markdown")
def quiz_spec_res() -> str:
    return read("quiz-package.md")


@mcp.resource("emile://scenario/mscb", mime_type="text/markdown")
def scenario_res() -> str:
    return read("mscb.md")


@mcp.resource("emile://course/{code}", mime_type="text/markdown")
def course_res(code: str) -> str:
    try:
        return read(course_file(code))
    except ValueError as e:
        raise ResourceNotFoundError(str(e)) from e


@mcp.resource("emile://antipatterns", mime_type="text/markdown")
def antipatterns_res() -> str:
    return read("antipatterns.md")


@mcp.tool(annotations=RO)
def emile_get_quiz_spec() -> str:
    """Return the RTC Standard Quiz Package specification (types, difficulty mix, JSON contract)."""
    return read("quiz-package.md")


@mcp.tool(annotations=RO)
def emile_get_scenario() -> str:
    """Return the Main Street Coffee & Books (MSCB) story bible summary: people, businesses, providers."""
    return read("mscb.md")


@mcp.tool(annotations=RO)
def emile_get_course_context(code: str) -> str:
    """Return course title, objective framework, rubric scale, and scenario provider. code: e.g. CNT160."""
    try:
        return read(course_file(code))
    except ValueError as e:
        raise ToolError(str(e)) from e


@mcp.tool(annotations=RO)
def emile_get_antipatterns() -> str:
    """Return the 11 anti-patterns Emile never produces."""
    return read("antipatterns.md")


# --- Validators -----------------------------------------------------------

@mcp.tool(annotations=RO)
def emile_lint_language(text: str) -> validators.LintResult:
    """Flag deficit-framing phrases ("simply", "obviously", "as you know", "this is basic") by line.
    Instructor-facing only; do not send student names, grades, or submissions (FERPA)."""
    return validators.lint_language(text)


@mcp.tool(annotations=RO)
def emile_validate_quiz(quiz_json: str) -> validators.QuizResult:
    """Check a quiz (JSON string, per emile://spec/quiz-package) for type counts, difficulty mix,
    objective mapping, all/none of the above, double negatives, and answer shape.
    Instructor-facing only; do not send student names, grades, or submissions (FERPA)."""
    return validators.validate_quiz(quiz_json)


@mcp.tool(annotations=RO)
def emile_check_load(text: str, new_terms: list[str]) -> validators.LoadResult:
    """Flag Markdown segments (split on headings) that introduce more than 5 of the given new terms.
    Instructor-facing only; do not send student names, grades, or submissions (FERPA)."""
    return validators.check_load(text, new_terms)


# --- HTTP transport (Lane 1 remote / Lane 2 Copilot Studio) ---------------

class BearerAuth:
    """ASGI middleware: require the token on every path except /healthz.

    Accepts `Authorization: Bearer <token>` (Claude Code, most MCP clients) or
    `X-API-Key: <token>` (Copilot Studio's API-key auth sends a bare header value).
    """

    def __init__(self, app, token: str):
        self.app, self.token = app, token.encode()

    def _authorized(self, headers: dict) -> bool:
        scheme, _, bearer = headers.get(b"authorization", b"").partition(b" ")
        supplied = bearer.strip() if scheme.lower() == b"bearer" else headers.get(b"x-api-key", b"").strip()
        return bool(supplied) and hmac.compare_digest(supplied, self.token)

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["path"] != "/healthz":
            if not self._authorized(dict(scope["headers"])):
                await send({"type": "http.response.start", "status": 401,
                            "headers": [(b"content-type", b"text/plain"), (b"www-authenticate", b"Bearer")]})
                await send({"type": "http.response.body", "body": b"unauthorized"})
                return
        await self.app(scope, receive, send)


def load_token() -> str:
    """Read the token from EMILE_TOKEN_FILE (systemd credential) or EMILE_TOKEN."""
    path = os.environ.get("EMILE_TOKEN_FILE")
    if not path and os.environ.get("CREDENTIALS_DIRECTORY"):
        path = str(Path(os.environ["CREDENTIALS_DIRECTORY"]) / "emile-token")
    if path and not Path(path).is_file():
        sys.exit(f"Token file {path} not found.")
    token = Path(path).read_text().strip() if path else os.environ.get("EMILE_TOKEN", "")
    if len(token) < 32:
        sys.exit("HTTP mode needs a token of 32+ characters in EMILE_TOKEN or EMILE_TOKEN_FILE. "
                 "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(32))'")
    return token


@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(_request):
    return PlainTextResponse("ok")


def http_app(token: str, host: str, port: int):
    allowed = [h.strip() for h in os.environ.get("EMILE_ALLOWED_HOSTS", "").split(",") if h.strip()]
    allowed += [f"127.0.0.1:{port}", f"localhost:{port}", f"{host}:{port}"]
    security = TransportSecuritySettings(enable_dns_rebinding_protection=True, allowed_hosts=allowed,
                                         allowed_origins=[f"https://{h}" for h in allowed])
    app = mcp.streamable_http_app(transport_security=security, host=host)
    return BearerAuth(app, token)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--transport", choices=["stdio", "http"], default=os.environ.get("EMILE_TRANSPORT", "stdio"))
    ap.add_argument("--host", default=os.environ.get("EMILE_HOST", "127.0.0.1"))
    ap.add_argument("--port", type=int, default=int(os.environ.get("EMILE_PORT", "8765")))
    args = ap.parse_args()

    if args.transport == "stdio":
        mcp.run()
        return

    import uvicorn
    uvicorn.run(http_app(load_token(), args.host, args.port), host=args.host, port=args.port,
                proxy_headers=False, server_header=False)


if __name__ == "__main__":
    main()
