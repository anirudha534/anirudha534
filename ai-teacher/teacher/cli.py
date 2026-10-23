"""Command line: python -m teacher <command>."""
import argparse
import re
import sys

from . import prompts
from .curriculum import Curriculum
from .progress import Progress
from .tutor import Tutor, TutorError

HELP = """\
Commands while learning (or just type your answer / question):
  /next      I got it, next step          /simpler   explain it differently, simpler
  /deeper    go deeper                    /example   one more example
  /stuck     give me a hint               /why       why does this matter?
  /quiz      quiz me now                  /recap     recap + exit quiz
  /done      finish lesson and save       /quit      save and stop for now
  <<<  ... >>>   paste several lines (code, errors) between these two markers
"""

BAR = 24


def bar(done, total):
    n = round(BAR * done / total) if total else 0
    return "#" * n + "-" * (BAR - n)


class Console:
    """Terminal input/output. Tests swap this for a scripted one."""

    def read(self, prompt):
        return input(prompt)

    def say(self, text=""):
        print(text)

    def stream(self, chunk):
        print(chunk, end="", flush=True)


def read_message(io):
    """One line, or many lines between <<< and >>> (for pasting code or errors)."""
    line = io.read("you> ")
    if line.strip() != "<<<":
        return line.strip()
    lines = []
    while (nxt := io.read("")).strip() != ">>>":
        lines.append(nxt)
    return "\n".join(lines).strip()


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "topic"


def run_session(tutor, prog, key, kickoff, label, io):
    """The teaching loop. Returns the grade dict if the lesson was finished, else None."""
    messages = prog.load_session(key)
    if messages:
        io.say(f"\nResuming where you left off ({label}). Type /recap to wrap up, /quit to stop.")
        if messages[-1]["role"] == "assistant":
            io.say("\nGuru> " + messages[-1]["content"])
    else:
        messages = [{"role": "user", "content": kickoff}]
        io.say(f"\n=== {label} ===\nType /help any time.")
        if not _teach(tutor, prog.config, messages, io):
            return None
        prog.save_session(key, messages)

    while True:
        try:
            text = read_message(io)
        except (EOFError, KeyboardInterrupt):
            prog.save_session(key, messages)
            io.say("\nSaved. See you soon!")
            return None
        if not text:
            continue
        if text == "/help":
            io.say(HELP)
        elif text == "/quit":
            prog.save_session(key, messages)
            io.say("Saved. Come back any time with the same command.")
            return None
        elif text == "/done":
            grade = _finish(tutor, prog.config, messages, io)
            if grade:
                return grade
        elif text.startswith("/") and text not in prompts.COMMANDS:
            io.say("Unknown command. Type /help.")
        else:
            messages.append({"role": "user", "content": prompts.COMMANDS.get(text, text)})
            if _teach(tutor, prog.config, messages, io):
                prog.save_session(key, messages)


def _teach(tutor, config, messages, io):
    """Stream one teacher reply and append it. On failure remove the unanswered message."""
    io.stream("\nGuru> ")
    try:
        text = tutor.reply(config, messages, on_text=io.stream)
    except TutorError as e:
        messages.pop()
        io.say(f"\n[problem] {e}\n")
        return False
    io.say("")
    messages.append({"role": "assistant", "content": text})
    return True


def _finish(tutor, config, messages, io):
    io.say("\nChecking how it went...")
    try:
        grade = tutor.grade(config, messages)
    except TutorError as e:
        io.say(f"[problem] {e}")
        return None
    if grade is None:
        raw = io.read("Rate yourself honestly: 0 lost, 1 shaky, 2 good, 3 could teach it > ").strip()
        grade = {"mastery": int(raw) if raw in ("0", "1", "2", "3") else 1, "weak": [], "notes": ""}
    labels = ["not yet - we will redo it", "shaky - we will revisit", "good", "excellent - you could teach it"]
    io.say(f"Mastery {grade['mastery']}/3: {labels[grade['mastery']]}. {grade['notes']}")
    if grade["weak"]:
        io.say("To revisit: " + "; ".join(grade["weak"]))
    return grade


def cmd_map(cur, prog, **_):
    print(f"Streak: {prog.streak()} day(s) | reviews due: {len(prog.due())}\n")
    for (num, title), lessons in cur.weeks().items():
        done = sum(prog.is_done(x.id) for x in lessons)
        print(f"Week {num:>2} [{bar(done, len(lessons))}] {done}/{len(lessons)}  {title}")


def cmd_progress(cur, prog, **_):
    cmd_map(cur, prog)
    weak = prog.weak_points()
    if weak:
        print("\nWeak spots to revisit: " + "; ".join(weak))
    nxt = prog.next_lesson(cur)
    print("\nNext up: " + (f"{nxt.id}  {nxt.label}" if nxt else "everything is done!"))


def _start(tutor, cur, prog, lesson, io, review=False):
    done_titles = [x.title for x in cur.lessons if prog.is_done(x.id) and x.id != lesson.id]
    ctx = prompts.lesson_context(lesson, done_titles, prog.weak_points(), cur.project_text(lesson))
    kickoff = (prompts.review_kickoff if review else prompts.lesson_kickoff)(ctx)
    key = ("review-" if review else "") + lesson.id
    grade = run_session(tutor, prog, key, kickoff, lesson.label, io)
    if grade:
        prog.mark(lesson.id, grade["mastery"], grade["weak"], grade["notes"])
        prog.clear_session(key)
        print("\nSaved. Tick these off on your checklist:")
        for t in lesson.tasks:
            print("  [ ] " + t["text"])


def cmd_start(cur, prog, tutor, io, lesson=None, **_):
    target = cur.find(lesson) if lesson and lesson != "next" else prog.next_lesson(cur)
    if target is None:
        sys.exit("No such lesson. Run `python -m teacher map` to see them, then use an id like w1-mon.")
    _start(tutor, cur, prog, target, io)


def cmd_review(cur, prog, tutor, io, **_):
    ids = prog.due()
    if not ids:
        print("Nothing due for review today. Great memory!")
        return
    print(f"{len(ids)} review(s) due. Starting with the oldest.")
    _start(tutor, cur, prog, cur.by_id[ids[0]], io, review=True)


def cmd_ask(cur, prog, tutor, io, topic, **_):
    topic = " ".join(topic)
    key = "free-" + slug(topic)
    grade = run_session(tutor, prog, key, prompts.free_kickoff(topic), f"Free topic: {topic}", io)
    if grade:
        prog.clear_session(key)


def cmd_config(cur, prog, name=None, language=None, theme=None, **_):
    for k, v in (("name", name), ("language", language), ("theme", theme)):
        if v:
            prog.config[k] = v
    prog.save()
    print("Settings:", prog.config)


def build_parser():
    p = argparse.ArgumentParser(prog="teacher", description="Guru: an explain-like-I'm-5 AI engineering teacher.")
    p.add_argument("--model", help="override the model (default claude-sonnet-5-5; try claude-opus-5-5 for hard topics)")
    p.add_argument("--effort", default="medium", choices=["low", "medium", "high", "xhigh", "max"])
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("start", help="start or resume a lesson (default: your next one)")
    s.add_argument("lesson", nargs="?")
    sub.add_parser("review", help="quick spaced-repetition check of something you learned")
    a = sub.add_parser("ask", help="learn any topic from scratch")
    a.add_argument("topic", nargs="+")
    sub.add_parser("map", help="roadmap with progress bars")
    sub.add_parser("progress", help="progress, streak, weak spots")
    c = sub.add_parser("config", help="set your name, language (e.g. Telugu), analogy theme")
    c.add_argument("--name")
    c.add_argument("--language")
    c.add_argument("--theme")
    return p


COMMANDS = {"start": cmd_start, "review": cmd_review, "ask": cmd_ask, "map": cmd_map,
            "progress": cmd_progress, "config": cmd_config}
NEEDS_TUTOR = {"start", "review", "ask"}


def main(argv=None):
    args = build_parser().parse_args(argv)
    cur, prog = Curriculum.load(), Progress()
    tutor = Tutor(model=args.model, effort=args.effort) if args.cmd in NEEDS_TUTOR else None
    kwargs = {k: v for k, v in vars(args).items() if k not in ("cmd", "model", "effort")}
    COMMANDS[args.cmd](cur=cur, prog=prog, tutor=tutor, io=Console(), **kwargs)
