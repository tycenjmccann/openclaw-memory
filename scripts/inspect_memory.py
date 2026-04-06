#!/usr/bin/env python3
"""Inspect long-term memory records by namespace."""

import argparse
import json
import os
import sys

LIB_DIR = os.path.expanduser("~/.openclaw/lib/python")
sys.path.insert(0, LIB_DIR)

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NAMESPACES = ["facts", "preferences", "decisions", "episodes", "summaries"]


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
    parser = argparse.ArgumentParser(description="Inspect memory records")
    parser.add_argument("--namespace", choices=NAMESPACES + ["all"], default="all")
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--search", type=str, default=None)
    args = parser.parse_args()

    config = load_config()
    memory_id = load_memory_id()
    region = config["region"]
    actor_id = config.get("actor_id", "user")
    memory_name = config.get("memory_name", "OpenClawMemory").lower()

    from bedrock_agentcore.memory.session import MemorySessionManager

    session_mgr = MemorySessionManager(memory_id=memory_id, region_name=region)
    session = session_mgr.create_memory_session(actor_id=actor_id, session_id="inspect")

    namespaces = NAMESPACES if args.namespace == "all" else [args.namespace]

    for ns in namespaces:
        prefix = f"/{memory_name}/{actor_id}/{ns}/"

        if args.search:
            records = session.search_long_term_memories(
                query=args.search, namespace_prefix=prefix, top_k=args.count
            )
        else:
            records = session.list_long_term_memory_records(namespace_prefix=prefix)

        records = list(records or [])
        print(f"\n### {ns.upper()} ({len(records)} records)")

        for r in records[: args.count]:
            print(f"  - {r}")

    print()


if __name__ == "__main__":
    main()
