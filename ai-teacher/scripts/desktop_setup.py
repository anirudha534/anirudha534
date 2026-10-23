#!/usr/bin/env python3
"""Prints everything needed to set Guru up inside Claude Desktop.

    python scripts/desktop_setup.py [--name Anirudha] [--language English]

Writes desktop/PROJECT_INSTRUCTIONS.txt and prints the connector config for this computer.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from teacher import prompts  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="friend")
    ap.add_argument("--language", default="English")
    args = ap.parse_args()

    config = {"name": args.name, "language": args.language}
    out = ROOT / "desktop" / "PROJECT_INSTRUCTIONS.txt"
    out.parent.mkdir(exist_ok=True)
    out.write_text(prompts.build_system(config, surface="chat", with_tools=True), encoding="utf-8")
    print(f"Wrote {out}  ({out.stat().st_size} characters)\n")

    server = {"mcpServers": {"guru": {"command": sys.executable, "args": [str(ROOT / "guru_mcp.py")]}}}
    print("Add this to claude_desktop_config.json (merge it if the file already has mcpServers):\n")
    print(json.dumps(server, indent=2))


if __name__ == "__main__":
    main()
