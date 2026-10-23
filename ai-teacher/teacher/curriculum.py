"""The roadmap as a list of lessons (one lesson = one day block of checkboxes)."""
import json
import re
from dataclasses import dataclass
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "curriculum.json"


@dataclass(frozen=True)
class Lesson:
    id: str
    month: int
    week: int
    week_title: str
    day: str
    title: str
    tasks: tuple

    @property
    def label(self):
        return f"Week {self.week} {self.day} - {self.title}"


class Curriculum:
    def __init__(self, data):
        self.months = data["months"]
        self.projects = data["projects"]
        self.lessons = []
        for w in data["weeks"]:
            for d in w["days"]:
                lid = f"w{w['week']}-{re.sub(r'[^a-z]+', '_', d['day'].lower())}"
                self.lessons.append(Lesson(
                    lid, w["month"], w["week"], w["title"], d["day"], d["title"], tuple(d["tasks"])))
        self.by_id = {x.id: x for x in self.lessons}

    @classmethod
    def load(cls, path=DATA):
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))

    def weeks(self):
        out = {}
        for x in self.lessons:
            out.setdefault((x.week, x.week_title), []).append(x)
        return out

    def project_text(self, lesson):
        """Spec of the project this lesson works on, if the roadmap names one."""
        blob = lesson.week_title + " " + " ".join(t["text"] for t in lesson.tasks)
        nums = re.findall(r"Project (\d)", blob)
        if "MCP" in lesson.week_title and not nums:
            nums = ["4"]
        return "\n\n".join(self.projects[n]["text"] for n in dict.fromkeys(nums) if n in self.projects)[:2500]

    def find(self, query):
        q = query.strip().lower()
        if q in self.by_id:
            return self.by_id[q]
        hits = [x for x in self.lessons if q in x.title.lower() or q in x.week_title.lower()]
        return hits[0] if hits else None
