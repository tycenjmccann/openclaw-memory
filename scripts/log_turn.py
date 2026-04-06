#!/usr/bin/env python3
"""Log a conversation turn to AgentCore Memory."""

import json
import os
import sys

LIB_DIR = os.path.expanduser("~/.openclaw/lib/python")
sys.path.insert(0, LIB_DIR)

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def main():
    if len(sys.argv) != 4:
        raise ValueError("Usage: log_turn.py <user_msg> <assistant_msg> <session_id>")

    user_msg, assistant_msg, session_id = sys.argv[1], sys.argv[2], sys.argv[3]

    memory_id_file = os.path.join(SKILL_DIR, ".memory-id")
    if not os.path.exists(memory_id_file):
        raise FileNotFoundError(f"Missing {memory_id_file} — run setup.py first")

    with open(memory_id_file) as f:
        memory_id = f.read().strip()

    with open(os.path.join(SKILL_DIR, "config.json")) as f:
        config = json.load(f)

    from bedrock_agentcore.memory import MemoryClient

    client = MemoryClient(region_name=config["region"])
    client.create_event(
        memory_id=memory_id,
        actor_id=config.get("actor_id", "user"),
        session_id=session_id,
        messages=[
            (user_msg, "user"),
            (assistant_msg, "assistant"),
        ],
    )

if __name__ == "__main__":
    main()
