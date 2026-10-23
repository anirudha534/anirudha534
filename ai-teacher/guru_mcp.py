#!/usr/bin/env python3
"""Guru as a Claude Desktop connector (local MCP server).

Gives Claude tools to look up your roadmap lessons and to save your progress, so the teaching itself
happens in Claude Desktop (no API key needed). Progress is shared with the command-line teacher.
Only needs:  pip install "mcp<2"
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mcp.server.fastmcp import FastMCP  # noqa: E402

from teacher import prompts  # noqa: E402
from teacher.curriculum import Curriculum  # noqa: E402
from teacher.progress import Progress  # noqa: E402

mcp = FastMCP("guru")
MASTERY = {0: "not yet", 1: "shaky", 2: "good", 3: "could teach it"}


def _lesson(cur, ref):
    lesson = cur.find(ref)
    if lesson is None:
        raise ValueError(f"No lesson matches '{ref}'. Use list_lessons to see ids like w1-mon.")
    return lesson


def _context(cur, prog, lesson):
    done = [x.title for x in cur.lessons if prog.is_done(x.id) and x.id != lesson.id]
    text = f"LESSON ID: {lesson.id}\n" + prompts.lesson_context(
        lesson, done, prog.weak_points(), cur.project_text(lesson))
    note = prog.resume_note(lesson.id)
    return text + (f"\n\nRESUME NOTE from the last chat: {note}" if note else "")


@mcp.tool()
def get_progress() -> str:
    """Student profile, streak, reviews due, weak spots and the next lesson. Call first in every new chat."""
    cur, prog = Curriculum.load(), Progress()
    c = prog.config
    done = sum(prog.is_done(x.id) for x in cur.lessons)
    nxt = prog.next_lesson(cur)
    due = prog.due()
    lines = [
        f"Student: {c['name']} | language: {c['language']} | analogy theme: {c['theme']}",
        f"Lessons finished: {done}/{len(cur.lessons)} | streak: {prog.streak()} day(s)",
        f"Reviews due: {', '.join(due) if due else 'none'}",
        f"Weak spots: {'; '.join(prog.weak_points()) or 'none yet'}",
        f"Next lesson: {nxt.id} - {nxt.label}" if nxt else "Next lesson: all done!",
    ]
    return "\n".join(lines)


@mcp.tool()
def get_next_lesson() -> str:
    """The student's next unfinished lesson with its roadmap checklist, project spec and weak spots."""
    cur, prog = Curriculum.load(), Progress()
    nxt = prog.next_lesson(cur)
    return _context(cur, prog, nxt) if nxt else "Every lesson is finished. Congratulate the student!"


@mcp.tool()
def get_lesson(lesson: str) -> str:
    """A specific lesson by id (like 'w3-wed') or by words in its title (like 'docker')."""
    cur, prog = Curriculum.load(), Progress()
    return _context(cur, prog, _lesson(cur, lesson))


@mcp.tool()
def list_lessons(week: int | None = None) -> str:
    """List lesson ids, titles and status ([x] done, [ ] todo). Optionally only one week (1-24)."""
    cur, prog = Curriculum.load(), Progress()
    rows = [x for x in cur.lessons if week is None or x.week == week]
    if not rows:
        raise ValueError("Weeks run from 1 to 24.")
    out, last = [], None
    for x in rows:
        if x.week != last:
            out.append(f"\nWeek {x.week}: {x.week_title}")
            last = x.week
        mark = "x" if prog.is_done(x.id) else " "
        out.append(f"  [{mark}] {x.id}: {x.day} - {x.title}")
    return "\n".join(out).strip()


@mcp.tool()
def get_due_reviews() -> str:
    """Lessons due for a spaced-repetition review today, oldest first, with their context."""
    cur, prog = Curriculum.load(), Progress()
    ids = prog.due()
    if not ids:
        return "No reviews are due today."
    return "\n\n---\n\n".join(_context(cur, prog, cur.by_id[i]) for i in ids[:3])


@mcp.tool()
def save_lesson_note(lesson_id: str, note: str) -> str:
    """Save where the student stopped mid-lesson so the next chat can resume exactly there."""
    cur, prog = Curriculum.load(), Progress()
    lesson = _lesson(cur, lesson_id)
    prog.set_resume(lesson.id, note[:500])
    return f"Saved a resume note for {lesson.id}."


@mcp.tool()
def save_progress(lesson_id: str, mastery: int, weak_points: list[str] | None = None, notes: str = "") -> str:
    """Record a finished lesson or review. mastery: 0 not yet, 1 shaky, 2 good, 3 could teach it (be honest)."""
    if mastery not in MASTERY:
        raise ValueError("mastery must be 0, 1, 2 or 3.")
    cur, prog = Curriculum.load(), Progress()
    lesson = _lesson(cur, lesson_id)
    prog.mark(lesson.id, mastery, [w[:80] for w in (weak_points or [])][:5], notes[:300])
    e = prog.entry(lesson.id)
    return (f"Saved {lesson.id}: mastery {mastery} ({MASTERY[mastery]}). Next review {e['due']}. "
            f"Streak: {prog.streak()} day(s).")


@mcp.tool()
def set_profile(name: str | None = None, language: str | None = None, theme: str | None = None) -> str:
    """Change the student's name, the language to explain in (e.g. 'Telugu'), or the analogy theme."""
    prog = Progress()
    for key, val in (("name", name), ("language", language), ("theme", theme)):
        if val:
            prog.config[key] = val[:60]
    prog.save()
    return f"Profile: {prog.config}"


if __name__ == "__main__":
    mcp.run()  # stdio, which is what Claude Desktop uses
