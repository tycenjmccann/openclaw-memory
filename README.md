# OpenClaw Memory

Persistent AI memory for [OpenClaw](https://github.com/openclaw) using AWS AgentCore Memory. Your assistant remembers facts, learns preferences, tracks decisions, and builds wisdom across conversations.

## Quick Start

```bash
git clone https://github.com/openclaw/openclaw-memory.git ~/.openclaw/skills/openclaw-memory
cd ~/.openclaw/skills/openclaw-memory
python3 setup.py          # creates memory resource, installs SDK, starts tailer
```

That's it. Every conversation is now automatically logged and extracted.

## How It Works

A session tailer runs as a systemd user service, watching your OpenClaw session `.jsonl` files in real-time. Each conversation turn is synced to AgentCore Memory, which runs extraction strategies in the background to pull out facts, preferences, decisions, summaries, and episodes.

> **Note on hooks:** OpenClaw's `message:sent` and `message:received` hook events are listed as "Future Events" and are not yet implemented. Once they ship, we'll switch to a hook-based approach for tighter integration. The session tailer is the reliable method for now.

## Beginner Guide

New to AWS? Run the guided setup:

```bash
python3 setup.py --guided
```

This walks you through:
1. Creating an AWS account (free tier works)
2. Setting up credentials
3. Creating the memory resource
4. Installing the session tailer service

Or deploy the CloudFormation stack for one-click IAM setup:

```bash
aws cloudformation deploy \
  --template-file aws/cloudformation.yaml \
  --stack-name openclaw-memory \
  --capabilities CAPABILITY_NAMED_IAM
```

## Memory Strategies

| Strategy | What It Captures | Example |
|----------|-----------------|---------|
| **Facts** | Technical details, project info, names | "Uses us-west-2 for all AWS resources" |
| **Preferences** | Work style, communication patterns | "Prefers concise responses" |
| **Decisions** | Choices made and reasoning | "Chose Sonnet for cost reasons" |
| **Summaries** | Session overviews | "Discussed recipe pipeline, fixed DynamoDB" |
| **Episodes** | Events + cross-session reflections | Pattern learning across conversations |

## Usage

### Session Startup

Run at the beginning of each session to hydrate context:

```bash
python3 scripts/get_context.py --turns 30 --compact
```

### Search Memory

```bash
python3 scripts/get_context.py --query "recipe pipeline" --turns 10
```

### Inspect Memory

```bash
python3 scripts/inspect_memory.py                          # all namespaces
python3 scripts/inspect_memory.py --namespace facts         # just facts
python3 scripts/inspect_memory.py --namespace decisions --count 20
python3 scripts/inspect_memory.py --search "DynamoDB"       # search across all
```

### Seed Memory

Import existing knowledge from a markdown file:

```bash
python3 scripts/seed_memory.py --file MEMORY.md
```

### Check Status

```bash
python3 setup.py --check
```

### Tailer Service Management

```bash
systemctl --user status memory-tailer     # check status
systemctl --user restart memory-tailer    # restart
journalctl --user -u memory-tailer -f     # follow logs
```

## Customization

Edit `config.json` to:
- Change extraction prompts per strategy
- Add new strategy namespaces
- Adjust `default_turns`, `max_message_length`
- Modify `skip_patterns` for messages to ignore

The config is designed to be modified by the assistant itself during use.

## Migration

Already have a `MEMORY.md` or similar knowledge file?

```bash
python3 scripts/seed_memory.py --file /path/to/MEMORY.md
```

Sections are parsed by markdown headings and logged as conversation turns for extraction.

## Cost Estimate

AgentCore Memory pricing (approximate):
- **Storage**: ~$0.25/GB/month for events
- **Extraction**: Model invocation costs per strategy (~$0.003/turn for Sonnet)
- **Search**: Negligible for typical usage

A typical personal assistant logging ~50 turns/day costs **< $5/month**.

## Project Structure

```
openclaw-memory/
├── SKILL.md                    # Skill definition
├── config.json                 # Strategy configuration
├── setup.py                    # One-command setup
├── scripts/
│   ├── session_tailer.py       # Watches sessions, syncs to memory (systemd service)
│   ├── memory_integration.py   # Python API for memory operations
│   ├── log_turn.py             # Log a single turn
│   ├── get_context.py          # Retrieve context for session
│   ├── inspect_memory.py       # Browse memory records
│   └── seed_memory.py          # Import from markdown
├── aws/
│   └── cloudformation.yaml     # IAM user + execution role
└── README.md
```

## License

MIT
