import { execFile } from "node:child_process";

const SKILL_DIR = "{{SKILL_DIR}}";
const LIB_DIR = "{{LIB_DIR}}";
const MAX_LEN = 2000;
const SKIP = /^(HEARTBEAT_OK|NO_REPLY|Read HEARTBEAT)/;

let userBuffer = "";

function sessionId(): string {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return `telegram-${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}`;
}

function truncate(s: string): string {
  return s.length > MAX_LEN ? s.slice(0, MAX_LEN) : s;
}

function logTurn(userMsg: string, assistantMsg: string): void {
  execFile(
    "python3",
    [`${SKILL_DIR}/scripts/log_turn.py`, userMsg, assistantMsg, sessionId()],
    { env: { ...process.env, PYTHONPATH: LIB_DIR } },
    (err, _stdout, stderr) => {
      if (err) console.error("[memory-sync] log_turn failed:", stderr || err.message);
    }
  );
}

export default function handler(event: { type: string; payload?: { text?: string; message?: string } }): void {
  const text = event.payload?.text || event.payload?.message || "";

  if (event.type === "message:received") {
    userBuffer = truncate(text);
    return;
  }

  if (event.type === "message:transcribed") {
    if (text) userBuffer = truncate(text);
    return;
  }

  if (event.type === "message:sent") {
    const assistantMsg = truncate(text);
    if (!userBuffer || !assistantMsg) return;
    if (SKIP.test(userBuffer) || SKIP.test(assistantMsg)) return;
    logTurn(userBuffer, assistantMsg);
    userBuffer = "";
  }
}
