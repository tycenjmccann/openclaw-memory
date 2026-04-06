#!/usr/bin/env python3
"""
Session Tailer — watches OpenClaw session .jsonl files and syncs
conversation turns to AgentCore Memory in near real-time.

Logs every user and assistant message individually — no pairing needed.
AgentCore Memory handles extraction and correlation on its own.
"""
import sys
import os
import json
import time
import glob
import argparse
import logging

sys.path.insert(0, os.path.expanduser("~/.openclaw/lib/python"))
sys.path.insert(0, os.path.expanduser("~/.openclaw/workspace/agentcore-memory"))

logging.basicConfig(
    level=logging.INFO,
    format="[memory-tailer] %(asctime)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

SESSIONS_DIR = os.path.expanduser("~/.openclaw/agents/main/sessions")
WATERMARK_FILE = os.path.expanduser("~/.openclaw/hooks/agentcore-memory-sync/tailer-watermark.json")
POLL_INTERVAL = 5

SKIP_PATTERNS = ["HEARTBEAT_OK", "NO_REPLY", "Read HEARTBEAT.md"]
MIN_LENGTH = 10


def extract_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "\n".join(parts)
    return str(content)


def should_skip(text):
    if not text or len(text) < MIN_LENGTH:
        return True
    return any(text.strip().startswith(p) for p in SKIP_PATTERNS)


def find_active_session():
    pattern = os.path.join(SESSIONS_DIR, "*.jsonl")
    files = glob.glob(pattern)
    return max(files, key=os.path.getmtime) if files else None


def load_watermark():
    try:
        with open(WATERMARK_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_watermark(wm):
    os.makedirs(os.path.dirname(WATERMARK_FILE), exist_ok=True)
    with open(WATERMARK_FILE, "w") as f:
        json.dump(wm, f)


def get_memory():
    from memory_integration import RexMemory
    return RexMemory()


def process_session(session_path, watermark, rex=None):
    key = os.path.basename(session_path)
    offset = watermark.get(key, 0)

    try:
        with open(session_path) as f:
            all_lines = f.readlines()
    except FileNotFoundError:
        return 0

    if offset >= len(all_lines):
        return 0

    new_lines = all_lines[offset:]
    basename = os.path.basename(session_path).replace(".jsonl", "")
    today = time.strftime("%Y%m%d")
    session_id = f"session-{today}-{basename[:8]}"

    synced = 0
    for line in new_lines:
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue

        if entry.get("type") != "message":
            continue

        msg = entry.get("message", {})
        role = msg.get("role")
        content = msg.get("content", "")
        text = extract_text(content)

        if role not in ("user", "assistant"):
            continue
        if should_skip(text):
            continue

        # Truncate to avoid API limits
        text = text[:2000]
        mem_role = "USER" if role == "user" else "ASSISTANT"

        try:
            if rex is None:
                rex = get_memory()
            rex.client.create_event(
                memory_id=rex.memory_id,
                actor_id=rex.actor_id,
                session_id=session_id,
                messages=[(text, mem_role)]
            )
            synced += 1
            log.info(f"Synced {role}: {text[:60]}...")
        except Exception as e:
            log.error(f"Failed to sync {role} message: {e}")

    if synced:
        log.info(f"{synced} messages synced from {key}")

    watermark[key] = len(all_lines)
    save_watermark(watermark)
    return synced


def run_once():
    session = find_active_session()
    if not session:
        log.warning("No active session found")
        return
    log.info(f"Processing: {session}")
    wm = load_watermark()
    synced = process_session(session, wm)
    log.info(f"Done. Synced {synced} messages.")


def run_tail():
    log.info(f"Starting session tailer (poll every {POLL_INTERVAL}s)")
    wm = load_watermark()
    current_session = None
    rex = None

    while True:
        try:
            session = find_active_session()
            if not session:
                time.sleep(POLL_INTERVAL)
                continue

            if session != current_session:
                log.info(f"Tracking session: {os.path.basename(session)}")
                current_session = session

            if rex is None:
                try:
                    rex = get_memory()
                except Exception as e:
                    log.error(f"Failed to init memory: {e}")
                    time.sleep(POLL_INTERVAL)
                    continue

            process_session(session, wm, rex)

        except KeyboardInterrupt:
            log.info("Shutting down")
            break
        except Exception as e:
            log.error(f"Error: {e}")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--session", help="Specific session file")
    args = parser.parse_args()

    if args.session:
        wm = load_watermark()
        process_session(args.session, wm)
    elif args.once:
        run_once()
    else:
        run_tail()
