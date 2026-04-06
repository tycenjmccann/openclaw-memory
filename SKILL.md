---
name: openclaw-memory
description: Persistent semantic memory for OpenClaw using AWS AgentCore Memory. Gives your assistant real memory across conversations — it remembers facts, learns your preferences, tracks decisions, and builds wisdom over time. Use when setting up memory, searching past conversations, or managing what your assistant remembers.
---

# OpenClaw Memory — Persistent AI Memory

Your assistant has persistent memory powered by AWS AgentCore Memory. Every conversation is automatically logged and extracted into searchable knowledge.

## What's Stored

| Type | What | Example |
|------|------|---------|
| **Facts** | Things learned from conversations | "Tycen uses us-west-2 for all AWS resources" |
| **Preferences** | How you like things done | "Prefers concise responses, surgical edits over rewrites" |
| **Decisions** | What was decided and why | "Chose Sonnet as default model for cost reasons" |
| **Summaries** | Session overviews | "Discussed recipe pipeline, fixed DynamoDB permissions" |
| **Episodes** | Discrete events + cross-session reflections | Pattern learning across conversations |

## How It Works

- **Automatic**: A session tailer watches your session `.jsonl` files and syncs every turn to AgentCore Memory in real-time. No manual action needed.
- **Extraction**: AgentCore runs 5 strategies in the background to extract facts, preferences, decisions, summaries, and episodes.
- **Retrieval**: At session start, run `get_context.py` to hydrate recent turns + relevant memories.

> **Note:** Once OpenClaw ships `message:sent`/`message:received` hook events (currently listed as "Future Events"), we'll switch to a hook-based approach. The session tailer is the reliable method for now.

## Session Startup

At the beginning of every main session, run:
```bash
python3 ~/.openclaw/skills/openclaw-memory/scripts/get_context.py --turns 30 --compact
```

This gives you:
- Last 30 conversation turns
- Recent decisions
- Optionally: semantic search results for the current topic

## Searching Memory

To find specific memories:
```bash
python3 ~/.openclaw/skills/openclaw-memory/scripts/get_context.py --query "recipe pipeline" --turns 10
```

## Inspecting Memory

To see what's stored:
```bash
python3 ~/.openclaw/skills/openclaw-memory/scripts/inspect_memory.py
python3 ~/.openclaw/skills/openclaw-memory/scripts/inspect_memory.py --namespace facts
python3 ~/.openclaw/skills/openclaw-memory/scripts/inspect_memory.py --namespace preferences
```

## Setup

If memory isn't set up yet, run:
```bash
python3 ~/.openclaw/skills/openclaw-memory/setup.py
```

This creates the AgentCore Memory resource and starts the session tailer service. Requires AWS credentials with AgentCore permissions.

## Customization

The assistant can modify `config.json` in this skill directory to:
- Change extraction prompts
- Add new strategy namespaces
- Adjust turn retrieval count
- Configure which events to skip

The config is designed to be modified by the assistant itself during use.
