import asyncio
import json
import sys
from pathlib import Path

import pytest

pytest.importorskip("mcp")

import guru_mcp  # noqa: E402
from mcp import ClientSession, StdioServerParameters  # noqa: E402
from mcp.client.stdio import stdio_client  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def text_of(result):
    content = result[0] if isinstance(result, tuple) else result
    return "".join(getattr(c, "text", "") for c in content)


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("TEACHER_HOME", str(tmp_path))
    return tmp_path


def call(name, **args):
    return text_of(asyncio.run(guru_mcp.mcp.call_tool(name, args)))


def test_tools_are_registered():
    names = {t.name for t in asyncio.run(guru_mcp.mcp.list_tools())}
    assert names == {"get_progress", "get_next_lesson", "get_lesson", "list_lessons", "get_due_reviews",
                     "save_lesson_note", "save_progress", "set_profile"}


def test_first_run_then_save_and_advance():
    assert "Next lesson: w1-mon" in call("get_progress")
    assert "LESSON ID: w1-mon" in call("get_next_lesson")
    out = call("save_progress", lesson_id="w1-mon", mastery=2, weak_points=["f-strings"], notes="ok")
    assert "mastery 2" in out
    assert "Next lesson: w1-tue" in call("get_progress")
    assert "f-strings" in call("get_progress")
    assert "[x] w1-mon" in call("list_lessons", week=1)


def test_resume_note_roundtrip():
    call("save_lesson_note", lesson_id="w1-mon", note="stopped after explaining variables")
    assert "stopped after explaining variables" in call("get_next_lesson")
    call("save_progress", lesson_id="w1-mon", mastery=3)
    assert "RESUME NOTE" not in call("get_lesson", lesson="w1-mon")  # cleared once finished


def test_profile_and_validation():
    assert "Telugu" in call("set_profile", language="Telugu")
    assert "Telugu" in call("get_progress")
    for name, args in (("save_progress", {"lesson_id": "w1-mon", "mastery": 7}),
                       ("get_lesson", {"lesson": "no-such-thing"}),
                       ("list_lessons", {"week": 99})):
        with pytest.raises(Exception):
            asyncio.run(guru_mcp.mcp.call_tool(name, args))


def test_due_reviews(tmp_path):
    from datetime import date, timedelta
    from teacher.progress import Progress
    Progress().mark("w1-mon", 2, today=date.today() - timedelta(days=5))
    assert "LESSON ID: w1-mon" in call("get_due_reviews")


def test_runs_over_stdio_like_claude_desktop(home):
    """Launch the server as a subprocess exactly as Claude Desktop does and call a tool."""
    async def go():
        params = StdioServerParameters(command=sys.executable, args=[str(ROOT / "guru_mcp.py")],
                                       env={"TEACHER_HOME": str(home), "PATH": ""})
        async with stdio_client(params) as (r, w), ClientSession(r, w) as session:
            await session.initialize()
            tools = await session.list_tools()
            res = await session.call_tool("get_progress", {})
            return len(tools.tools), res.content[0].text
    n, text = asyncio.run(go())
    assert n == 8 and "Next lesson: w1-mon" in text


def test_desktop_instructions_generate(tmp_path):
    from teacher import prompts
    text = prompts.build_system({"name": "Anirudha"}, surface="chat", with_tools=True)
    assert "get_progress" in text and "save_progress" in text and "light markdown" in text
    assert "terminal" not in prompts.build_system({}, surface="chat").lower()
    assert "get_progress" not in prompts.build_system({})  # terminal build has no tool talk
