# Guru - an "explain it like I'm 5" teacher for your AI Engineer roadmap

A terminal tutor that walks you through all 24 weeks (306 checklist items) of
`AI_Engineer_Roadmap_FINAL.docx`, one day at a time.

## What it does differently from just chatting with an AI

- **Teaches with a ladder:** picture -> tiny example -> real name -> grown-up detail -> check question.
- **Never moves on until you show you understood.** It asks you to explain things back, predict output,
  or spot a bug, and re-teaches with a *different* picture if you miss.
- **Makes you build.** Hints, not answers. You type the code; it reads your errors with you.
- **Remembers you.** Progress bars, streak, weak spots, and spaced-repetition reviews (1, 3, 7, 14, 30 days).
- **Resumes** any unfinished lesson exactly where you stopped.
- **Language:** can explain in Telugu/Hindi while keeping technical words in English.

## Option A: inside Claude Desktop (no API key needed)

Uses your normal Claude subscription. Claude does the teaching in a Project; a tiny local connector
(`guru_mcp.py`) saves your progress, so every new chat knows where you are.

1. `pip install "mcp<2"`  (the `<2` matters - version 2 changed its API)
2. `python scripts/desktop_setup.py --name Anirudha`
   It writes `desktop/PROJECT_INSTRUCTIONS.txt` and prints a block of JSON for this computer.
3. Claude Desktop -> Settings -> Developer -> **Edit Config**. Paste/merge the JSON into
   `claude_desktop_config.json` (if it already has `mcpServers`, add just the `"guru"` entry).
   Fully quit Claude Desktop (system tray -> Quit) and reopen it. A "guru" connector with 8 tools should appear.
4. Create a **Project** called "Guru". In its instructions, paste all of `desktop/PROJECT_INSTRUCTIONS.txt`.
   (Optional: add your roadmap .docx to the project's files.)
5. Open a chat inside the project and say "let's start". Say `simpler`, `next`, `stuck`, `recap`, `done` anytime.

If Settings has no Developer section, or the connector does not appear, your work/org account may block local
connectors. Guru still works with just the Project instructions - it will tell you progress is not being saved
and ask which lesson you are on.

Progress is stored in `~/.ai-teacher/` and is shared with the command-line version below.

## Option B: command line with an API key

## Set up (5 minutes)

1. Get an API key at console.anthropic.com (and set a monthly spend limit there).
2. In a terminal:

```
cd ai-teacher
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...      # Windows PowerShell: $env:ANTHROPIC_API_KEY="sk-ant-..."
python -m teacher config --name Anirudha --language English
python -m teacher start                   # begins at Week 1, Monday
```

## Commands

| Command | What it does |
|---|---|
| `python -m teacher start` | next lesson (or resume the unfinished one) |
| `python -m teacher start w3-wed` | a specific lesson (ids shown by `map`) |
| `python -m teacher review` | quick quiz on something due for review |
| `python -m teacher ask "what is an API"` | learn any topic from scratch |
| `python -m teacher map` / `progress` | roadmap bars, streak, weak spots |
| `python -m teacher config --language Telugu` | change name / language / analogy theme |

Inside a lesson: just type your answers. `/next` `/simpler` `/deeper` `/example` `/stuck` `/why` `/quiz`
`/recap` `/done` `/quit` (type `/help`). To paste code or an error, type `<<<`, paste, then `>>>`.

Progress is saved in `~/.ai-teacher/` (change with `TEACHER_HOME`).

## Model and cost

Default model is `claude-sonnet-5-5` (good and cheap for teaching). For a hard topic try
`python -m teacher --model claude-opus-5-5 start`. Cost depends on how long you chat; watch usage in the console.

## Status / honest notes

- The connector is tested end to end over stdio (the way Claude Desktop launches it), but **not yet inside the
  real Claude Desktop app** - the first chat is the real test.
- Unit tests (`pytest tests`) cover the roadmap parser, spaced repetition, lesson flow, resume, and error
  handling using a fake client. **It has not been run against the live API yet** - the first real lesson is the
  real test; if anything misbehaves, tell me what you saw.
- If the model refuses or the reply is cut off, you get a message (`/continue` resumes a cut-off reply).
- `data/curriculum.json` was generated from your roadmap with `scripts/extract_roadmap.py`; re-run it if you edit the docx.
