import json

import pytest
from mcp import Client
from starlette.testclient import TestClient

import server

pytestmark = pytest.mark.anyio

EXPECTED_TOOLS = {
    "emile_get_quiz_spec",
    "emile_get_scenario",
    "emile_get_course_context",
    "emile_get_antipatterns",
    "emile_lint_language",
    "emile_validate_quiz",
    "emile_check_load",
}


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def test_every_tool_is_read_only():
    async with Client(server.mcp) as c:
        tools = {t.name: t for t in (await c.list_tools()).tools}
    assert set(tools) == EXPECTED_TOOLS
    for t in tools.values():
        a = t.annotations
        assert (a.read_only_hint, a.destructive_hint, a.open_world_hint) == (True, False, False), t.name


async def test_resources_are_mirrored_by_tools():
    async with Client(server.mcp) as c:
        uris = {str(r.uri) for r in (await c.list_resources()).resources}
        templates = {r.uri_template for r in (await c.list_resource_templates()).resource_templates}
        assert uris == {"emile://spec/quiz-package", "emile://scenario/mscb", "emile://antipatterns"}
        assert templates == {"emile://course/{code}"}
        pairs = [
            ("emile://spec/quiz-package", "emile_get_quiz_spec", {}),
            ("emile://scenario/mscb", "emile_get_scenario", {}),
            ("emile://antipatterns", "emile_get_antipatterns", {}),
            ("emile://course/CNT160", "emile_get_course_context", {"code": "CNT160"}),
        ]
        for uri, tool, args in pairs:
            res_text = (await c.read_resource(uri)).contents[0].text
            tool_text = (await c.call_tool(tool, args)).content[0].text
            assert res_text == tool_text, uri


async def test_prompt_includes_system_course_and_task():
    async with Client(server.mcp) as c:
        text = (await c.get_prompt("emile", {"task": "Write a lab", "course": "cnt 290"})).messages[0].content.text
    assert text.startswith("# Emile — System Prompt")
    assert "Course Context — CNT 290" in text
    assert text.endswith("## Task\nWrite a lab")


@pytest.mark.parametrize("code", ["CNT160", "cnt 180", "CNT-256", "cnt_290"])
def test_course_codes_normalize(code):
    assert server.course_file(code).startswith("course-cnt")


@pytest.mark.parametrize("code", ["../emile-system", "CNT999", "", "course-cnt160"])
def test_unknown_course_rejected(code):
    with pytest.raises(ValueError):
        server.course_file(code)


async def test_unknown_course_tool_error_is_readable():
    async with Client(server.mcp) as c:
        res = await c.call_tool("emile_get_course_context", {"code": "../etc/passwd"})
    assert res.is_error and "Known courses: CNT160" in res.content[0].text


async def test_validator_tools_return_structured_results(valid_quiz):
    async with Client(server.mcp) as c:
        quiz = await c.call_tool("emile_validate_quiz", {"quiz_json": json.dumps(valid_quiz)})
        lint = await c.call_tool("emile_lint_language", {"text": "simply"})
    assert quiz.structured_content["pass"] is True
    assert lint.structured_content == {"pass": False, "hits": [{"line": 1, "phrase": "simply"}]}


# --- HTTP transport ---------------------------------------------------------

TOKEN = "t" * 40


@pytest.fixture
def http():
    with TestClient(server.http_app(TOKEN, "127.0.0.1", 8765), base_url="http://127.0.0.1:8765") as client:
        yield client


def test_healthz_is_open(http):
    assert http.get("/healthz").text == "ok"


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer wrong"}, {"Authorization": f"Basic {TOKEN}"},
                                     {"X-API-Key": "wrong"}, {"Authorization": "Bearer "}])
def test_mcp_endpoint_requires_token(http, headers):
    assert http.post("/mcp", headers=headers, json={}).status_code == 401


@pytest.mark.parametrize("auth", [{"Authorization": f"Bearer {TOKEN}"}, {"X-API-Key": TOKEN}])
def test_mcp_endpoint_accepts_token(http, auth):
    r = http.post(
        "/mcp",
        headers={**auth, "Accept": "application/json, text/event-stream"},
        json={"jsonrpc": "2.0", "id": 1, "method": "initialize",
              "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                         "clientInfo": {"name": "test", "version": "0"}}},
    )
    assert r.status_code == 200, r.text


def test_short_token_refused(monkeypatch):
    monkeypatch.delenv("EMILE_TOKEN_FILE", raising=False)
    monkeypatch.delenv("CREDENTIALS_DIRECTORY", raising=False)
    monkeypatch.setenv("EMILE_TOKEN", "short")
    with pytest.raises(SystemExit):
        server.load_token()


def test_token_file_wins(monkeypatch, tmp_path):
    f = tmp_path / "tok"
    f.write_text(TOKEN + "\n")
    monkeypatch.setenv("EMILE_TOKEN_FILE", str(f))
    monkeypatch.setenv("EMILE_TOKEN", "ignored")
    assert server.load_token() == TOKEN


async def test_stdio_launch():
    import sys

    from mcp import StdioServerParameters

    params = StdioServerParameters(command=sys.executable, args=[str(server.Path(server.__file__))])
    async with Client(params) as c:
        assert {t.name for t in (await c.list_tools()).tools} == EXPECTED_TOOLS


def test_missing_token_file_is_an_error(monkeypatch, tmp_path):
    monkeypatch.setenv("EMILE_TOKEN_FILE", str(tmp_path / "absent"))
    monkeypatch.setenv("EMILE_TOKEN", TOKEN)
    with pytest.raises(SystemExit):
        server.load_token()
