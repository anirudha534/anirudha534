from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from teacher import prompts
from teacher.cli import run_session, slug
from teacher.curriculum import Curriculum
from teacher.progress import Progress
from teacher.tutor import Tutor, TutorError, parse_grade


# ---------- fake Claude client ----------
class FakeStream:
    def __init__(self, text, stop="end_turn"):
        self.text_stream = iter([text[: len(text) // 2], text[len(text) // 2:]])
        self.final = SimpleNamespace(content=[SimpleNamespace(type="text", text=text)], stop_reason=stop)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def get_final_message(self):
        return self.final


class FakeClient:
    def __init__(self, replies, grade='{"mastery": 2, "weak": ["async"], "notes": "good"}'):
        self.replies, self.grade, self.calls = list(replies), grade, []
        self.messages = SimpleNamespace(stream=self._stream, create=self._create)

    def _stream(self, **kw):
        self.calls.append(kw)
        return FakeStream(self.replies.pop(0))

    def _create(self, **kw):
        self.calls.append(kw)
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=self.grade)], stop_reason="end_turn")


class ScriptIO:
    def __init__(self, inputs):
        self.inputs, self.out = list(inputs), []

    def read(self, prompt):
        if not self.inputs:
            raise EOFError
        return self.inputs.pop(0)

    def say(self, text=""):
        self.out.append(text)

    def stream(self, chunk):
        self.out.append(chunk)

    @property
    def text(self):
        return "".join(self.out)


# ---------- curriculum ----------
def test_curriculum_has_whole_roadmap():
    cur = Curriculum.load()
    assert len({x.week for x in cur.lessons}) == 24
    assert sum(len(x.tasks) for x in cur.lessons) == 306
    assert len(cur.by_id) == len(cur.lessons)  # ids are unique


def test_find_and_project_text():
    cur = Curriculum.load()
    assert cur.find("w1-mon").title.startswith("Python basics")
    assert cur.find("nonsense-xyz") is None
    mcp = next(x for x in cur.lessons if x.week == 6)
    assert "MCP" in cur.project_text(mcp)


# ---------- progress / spaced repetition ----------
def test_leitner_boxes_and_due(tmp_path):
    p, d0 = Progress(tmp_path), date(2026, 1, 1)
    p.mark("a", 3, today=d0)
    assert p.entry("a")["box"] == 2 and p.entry("a")["due"] == "2026-01-04"
    p.mark("a", 3, today=d0)
    assert p.entry("a")["box"] == 3
    p.mark("a", 1, today=d0)  # shaky resets to box 1
    assert p.entry("a")["box"] == 1
    assert p.due(d0) == [] and p.due(d0 + timedelta(days=1)) == ["a"]
    p.mark("b", 0, today=d0)  # not understood: not done, never "due"
    assert not p.is_done("b") and "b" not in p.due(d0 + timedelta(days=99))


def test_streak_and_persistence(tmp_path):
    p, today = Progress(tmp_path), date(2026, 1, 10)
    for i in (0, 1, 2):
        p.mark("l", 2, today=today - timedelta(days=i))
    assert p.streak(today) == 3
    assert p.streak(today + timedelta(days=2)) == 0
    assert Progress(tmp_path).is_done("l")  # reloaded from disk


def test_next_lesson_skips_done(tmp_path):
    cur, p = Curriculum.load(), Progress(tmp_path)
    assert p.next_lesson(cur).id == "w1-mon"
    p.mark("w1-mon", 2)
    assert p.next_lesson(cur).id == "w1-tue"


# ---------- grading parser ----------
def test_parse_grade():
    assert parse_grade('Sure: {"mastery": 3, "weak": ["a"], "notes": "n"}')["mastery"] == 3
    assert parse_grade("no json here") is None
    assert parse_grade('{"mastery": 9}') is None
    assert parse_grade('{"weak": []}') is None


# ---------- tutor request shape ----------
def test_reply_request_shape_and_text():
    client = FakeClient(["Hello there"])
    t = Tutor(client=client, effort="low")
    chunks = []
    out = t.reply({"name": "Anirudha"}, [{"role": "user", "content": "hi"}], on_text=chunks.append)
    call = client.calls[0]
    assert out == "Hello there" and "".join(chunks) == "Hello there"
    assert call["model"] == "claude-sonnet-5-5"
    assert call["output_config"] == {"effort": "low"}
    assert call["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert "Anirudha" in call["system"][0]["text"]
    assert "temperature" not in call and "thinking" not in call


def test_truncated_and_refused_replies():
    t = Tutor(client=FakeClient(["part"]))
    t.client.messages.stream = lambda **kw: FakeStream("part", stop="max_tokens")
    assert "/continue" in t.reply({}, [{"role": "user", "content": "x"}])
    t.client.messages.stream = lambda **kw: FakeStream("", stop="refusal")
    with pytest.raises(TutorError):
        t.reply({}, [{"role": "user", "content": "x"}])


def test_language_setting_changes_prompt():
    assert "Telugu" in prompts.build_system({"language": "Telugu"})
    assert "Telugu" not in prompts.build_system({})


# ---------- full lesson flow ----------
def make(tmp_path, replies, inputs):
    prog = Progress(tmp_path)
    return Tutor(client=FakeClient(replies)), prog, ScriptIO(inputs)


def test_lesson_flow_commands_and_done(tmp_path):
    tutor, prog, io = make(tmp_path, ["Q1?", "Step 1", "Simpler pic", "Recap"],
                           ["I think it is a box", "/simpler", "/recap", "/done"])
    grade = run_session(tutor, prog, "k", "KICKOFF", "Test lesson", io)
    assert grade["mastery"] == 2
    sent = [m["content"] for m in tutor.client.calls[-2]["messages"] if m["role"] == "user"]
    assert sent[0] == "KICKOFF" and prompts.COMMANDS["/recap"] in sent  # slash command expanded
    assert "Guru> Q1?" in io.text


def test_multiline_paste(tmp_path):
    tutor, prog, io = make(tmp_path, ["Q?", "ok"], ["<<<", "line1", "line2", ">>>"])
    run_session(tutor, prog, "k", "K", "L", io)
    assert prog.load_session("k")[2]["content"] == "line1\nline2"  # kickoff, Q, pasted answer


def test_quit_saves_and_resumes(tmp_path):
    tutor, prog, io = make(tmp_path, ["First", "Second"], ["my answer", "/quit"])
    assert run_session(tutor, prog, "k", "K", "L", io) is None
    assert len(prog.load_session("k")) == 4  # kickoff, Q, answer, reply
    tutor2, _, io2 = make(tmp_path, [], ["/quit"])
    run_session(tutor2, Progress(tmp_path), "k", "K", "L", io2)
    assert "Resuming" in io2.text and "Second" in io2.text and tutor2.client.calls == []


def test_api_failure_does_not_corrupt_history(tmp_path):
    tutor, prog, io = make(tmp_path, ["Q?"], ["hello", "/quit"])
    real = tutor.client.messages.stream
    state = {"n": 0}

    def flaky(**kw):
        state["n"] += 1
        if state["n"] == 2:
            raise TutorError("boom")  # surfaces like any teacher failure
        return real(**kw)

    tutor.client.messages.stream = flaky
    run_session(tutor, prog, "k", "K", "L", io)
    roles = [m["role"] for m in prog.load_session("k")]
    assert roles == ["user", "assistant"]  # the failed turn was removed, alternation intact
    assert "[problem] boom" in io.text


def test_unknown_command_and_slug(tmp_path):
    tutor, prog, io = make(tmp_path, ["Q?"], ["/bogus", "/quit"])
    run_session(tutor, prog, "k", "K", "L", io)
    assert "Unknown command" in io.text
    assert slug("What is an API?!") == "what-is-an-api"
