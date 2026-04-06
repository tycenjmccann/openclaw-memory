---
name: openclaw-memory-sync
description: Logs conversation turns to AgentCore Memory for persistent recall.
events:
  - message:received
  - message:transcribed
  - message:sent
---

# Memory Sync Hook

Pairs inbound user messages with outbound assistant responses and logs each turn to AWS AgentCore Memory.

## Event Flow

1. `message:received` — Buffers the raw inbound user message
2. `message:transcribed` — Overwrites buffer with cleaned transcript (if available)
3. `message:sent` — Pairs buffered user message with assistant response, logs the turn

## Skipped Messages

- `HEARTBEAT_OK`
- `NO_REPLY`
- Messages matching skip patterns in `config.json`

## Dependencies

- Python 3 with `bedrock_agentcore` SDK installed to `~/.openclaw/lib/python`
- Valid `.memory-id` file in the skill directory
