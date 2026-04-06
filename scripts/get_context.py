#!/usr/bin/env python3
"""Retrieve recent turns and semantic memories for session hydration."""

import argparse
import json
import os
import sys
from datetime import datetime

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


def main():
    parser = argparse.ArgumentParser(description="Get memory context")
    parser.add_argument("--turns", type=int, default=30)
    parser.add_argument("--query", type=str, default=None)
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()

    config = load_config()
    memory_id = load_memory_id()
    region = config["region"]
    actor_id = config.get("actor_id", "user")
    session_id = f"{config.get('session_prefix', 'telegram')}-{datetime.now().strftime('%Y%m%d')}"

    from bedrock_agentcore.memory import MemoryClient
    from bedrock_agentcore.memory.session import MemorySessionManager

    client = MemoryClient(region_name=region)

    # Recent turns
    turns = client.get_last_k_turns(
        memory_id=memory_id, actor_id=actor_id, session_id=session_id, k=args.turns
    )

    if turns:
        print("## Recent Turns\n")
        for turn in turns:
            if isinstance(turn, list):
                for msg in turn:
                    role = msg.get("role", "?")
                    text = msg.get("content", {}).get("text", str(msg.get("content", "")))
                    if args.compact:
                        text = text[:200]
                    print(f"**{role}**: {text}")
            else:
                print(str(turn)[:200] if args.compact else str(turn))
        print()

    # Semantic search
    if args.query:
        session_mgr = MemorySessionManager(memory_id=memory_id, region_name=region)
        session = session_mgr.create_memory_session(actor_id=actor_id, session_id=session_id)
        results = session.search_long_term_memories(
            query=args.query, namespace_prefix="/", top_k=5
        )
        if results:
            print("## Search Results\n")
            for r in results:
                print(f"- {r}")
            print()

    # Recent decisions
    session_mgr = MemorySessionManager(memory_id=memory_id, region_name=region)
    session = session_mgr.create_memory_session(actor_id=actor_id, session_id=session_id)
    decisions = session.list_long_term_memory_records(namespace_prefix="/")
    decision_records = [d for d in (decisions or []) if "decision" in str(d).lower()]
    if decision_records:
        print("## Recent Decisions\n")
        for d in decision_records[:10]:
            print(f"- {d}")
        print()


if __name__ == "__main__":
    main()
