"""Saved progress + spaced repetition (Leitner boxes). Pure logic, no network."""
import json
import os
from datetime import date, timedelta
from pathlib import Path

INTERVALS = [1, 3, 7, 14, 30]  # days until review, by box 1..5
DEFAULT_CONFIG = {"name": "friend", "language": "English", "theme": "Indian everyday life"}


def home():
    return Path(os.environ.get("TEACHER_HOME", Path.home() / ".ai-teacher"))


class Progress:
    def __init__(self, root=None):
        self.root = Path(root) if root else home()
        self.path = self.root / "progress.json"
        self.data = {"config": dict(DEFAULT_CONFIG), "lessons": {}, "days": []}
        if self.path.exists():
            self.data.update(json.loads(self.path.read_text(encoding="utf-8")))
            self.data["config"] = {**DEFAULT_CONFIG, **self.data["config"]}

    @property
    def config(self):
        return self.data["config"]

    def save(self):
        self.root.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=1), encoding="utf-8")
        os.replace(tmp, self.path)

    def entry(self, lesson_id):
        return self.data["lessons"].get(lesson_id)

    def is_done(self, lesson_id):
        e = self.entry(lesson_id)
        return bool(e and e["mastery"] >= 1)

    def mark(self, lesson_id, mastery, weak=(), notes="", today=None):
        """Record a finished lesson or review. Higher mastery climbs the Leitner box."""
        today = today or date.today()
        old = self.entry(lesson_id)
        box = old["box"] if old else 1
        box = min(box + 1, len(INTERVALS)) if mastery == 3 else box if mastery == 2 else 1
        self.data["lessons"][lesson_id] = {
            "mastery": mastery,
            "box": box,
            "due": (today + timedelta(days=INTERVALS[box - 1])).isoformat(),
            "weak": list(weak),
            "notes": notes,
            "last": today.isoformat(),
        }
        if today.isoformat() not in self.data["days"]:
            self.data["days"].append(today.isoformat())
        self.save()

    def due(self, today=None):
        today = (today or date.today()).isoformat()
        rows = [(e["due"], k) for k, e in self.data["lessons"].items() if e["mastery"] >= 1 and e["due"] <= today]
        return [k for _, k in sorted(rows)]

    def weak_points(self, limit=6):
        out = []
        for e in self.data["lessons"].values():
            out.extend(e["weak"])
        return out[-limit:]

    def streak(self, today=None):
        today = today or date.today()
        days = {date.fromisoformat(d) for d in self.data["days"]}
        n, d = 0, today if today in days else today - timedelta(days=1)
        while d in days:
            n, d = n + 1, d - timedelta(days=1)
        return n

    def next_lesson(self, cur):
        return next((x for x in cur.lessons if not self.is_done(x.id)), None)

    # conversations, so a lesson can be resumed tomorrow
    def session_path(self, key):
        return self.root / "sessions" / f"{key}.json"

    def load_session(self, key):
        p = self.session_path(key)
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []

    def save_session(self, key, messages):
        p = self.session_path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(messages, ensure_ascii=False), encoding="utf-8")

    def clear_session(self, key):
        self.session_path(key).unlink(missing_ok=True)
