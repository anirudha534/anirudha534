#!/usr/bin/env python3
"""Turn the roadmap (docx -> plain text via pandoc) into data/curriculum.json.

    pandoc -t plain --wrap=none AI_Engineer_Roadmap_FINAL.docx -o roadmap.txt
    python scripts/extract_roadmap.py roadmap.txt data/curriculum.json
"""
import json
import re
import sys

MONTH = re.compile(r"^\|\s*(Month (\d+) — .+?)\s*\|$")
WEEK = re.compile(r"^Week (\d+) — (.+)$")
D = r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)"
DAY = re.compile(rf"^({D}(?:[–-]{D})?)(?: \(([^)]*)\))?(?: — (.+))?$")
TASK = re.compile(r"^\s*☐ (.+)$")
PROJECT = re.compile(r"^\|\s*(Project (\d) — .+?)\s*\|$")


def parse(lines):
    months, weeks, projects = {}, [], {}
    month, week, day, project = None, None, None, None
    for raw in lines:
        line = raw.rstrip()
        if m := MONTH.match(line):
            month = int(m.group(2))
            months[month] = {"title": m.group(1), "theme": ""}
            week = day = project = None
        elif m := PROJECT.match(line):
            project = int(m.group(2))
            projects[project] = {"title": m.group(1), "text": []}
            week = day = None
        elif project and line.startswith("|"):
            text = line.strip("| ").strip()
            if text:
                projects[project]["text"].append(text)
        elif m := WEEK.match(line):
            week = {"week": int(m.group(1)), "month": month, "title": m.group(2), "days": []}
            weeks.append(week)
            day = project = None
        elif week and (m := DAY.match(line)):
            title = " ".join(x for x in (m.group(3), f"({m.group(2)})" if m.group(2) else "") if x)
            day = {"day": m.group(1), "title": title or m.group(1), "tasks": []}
            week["days"].append(day)
        elif day and (m := TASK.match(line)):
            day["tasks"].append(m.group(1).strip())
        elif month and not week and not project and line.startswith("|") and not months[month]["theme"]:
            text = line.strip("| ").strip()
            if text and not text.startswith("Month"):
                months[month]["theme"] = text
    for w in weeks:
        for d in w["days"]:
            for i, t in enumerate(d["tasks"]):
                d["tasks"][i] = {"id": f"w{w['week']}-{re.sub(r'[^a-z]+', '_', d['day'].lower())}-{i + 1}", "text": t}
    for p in projects.values():
        p["text"] = "\n".join(p["text"])
    return {"months": months, "weeks": weeks, "projects": projects}


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    data = parse(open(src, encoding="utf-8").read().splitlines())
    json.dump(data, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    n = sum(len(d["tasks"]) for w in data["weeks"] for d in w["days"])
    print(f"{len(data['weeks'])} weeks, {n} tasks, {len(data['projects'])} projects")
