#!/usr/bin/env python3
"""Seed memory from a MEMORY.md markdown file."""

import argparse
import json
import os
import re
import sys

LIB_DIR = os.path.expanduser("~/.openclaw/lib/python")
sys.path.insert(0, LIB_DIR)

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_config():
    with open(os.path.join(SKILL_DIR, "config.json")) as f:
        return json.load(f)


def load_memory_id():
    p = os.path.join(SKILL_DIR, ".memory-id")
    if not os.path.exists(p):
        raise FileNotFoundError(f"Missing {p} — run setup.py first")
    with open(p) as f:
        return f.read().strip()


def parse_sections(text):
    """Split markdown into (heading, body) tuples."""
    parts = re.split(r"^(#{1,3}\s+.+)$", text, flags=re.MULTILINE)
    sections = []
    heading = "Introduction"
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if re.match(r"^#{1,3}\s+", part):
            heading = re.sub(r"^#+\s*", "", part)
        else:
            sections.append((heading, part))
    return sections


def main():
    parser = argparse.ArgumentParser(description="Seed memory from markdown")
    parser.add_argument("--file", required=True, help="Path to MEMORY.md")
    args = parser.parse_args()

    if not os.path.exists(args.file):
        raise FileNotFoundError(f"File not found: {args.file}")

    config = load_config()
    memory_id = load_memory_id()

    with open(args.file) as f:
        content = f.read()

    sections = parse_sections(content)
    if not sections:
        raise ValueError("No sections found in file")

    from bedrock_agentcore.memory import MemoryClient

    client = MemoryClient(region_name=config["region"])
    actor_id = config.get("actor_id", "user")

    for i, (heading, body) in enumerate(sections):
        user_msg = f"Remember this about {heading}"
        assistant_msg = body[:2000]
        client.create_event(
            memory_id=memory_id,
            actor_id=actor_id,
            session_id="seed-import",
            messages=[(user_msg, "user"), (assistant_msg, "assistant")],
        )
        print(f"  ✅ [{i + 1}/{len(sections)}] {heading}")

    print(f"\n✅ Seeded {len(sections)} sections from {args.file}")


if __name__ == "__main__":
    main()
