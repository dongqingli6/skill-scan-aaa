---
name: bet-kickoff
description: "Automate Preflight + Shape at the start of a Base AA Explorer bet"
allowed-tools: Read Grep Glob Bash
---

## Trigger
At bet start

## Input
- Project: Base AA Explorer
- Tech: Python (FastAPI), TypeScript (Next.js 14), SQLite (MVP)
- Acceptance: Confirm real-time UserOp collection within 5 minutes; dashboard load time < 2 seconds

## Process
1. Scan the codebase structure
2. Confirm the baseline: build=`cd backend && pip install -e ".[dev]" && cd ../frontend && npm run build`, test=`cd backend && pytest && cd ../frontend && npm test`
3. Confirm `no_touch`: ["node_modules/", ".env", "*.key"]
4. Verify the 4 lock-in conditions (Problem/Appetite/No-go/Acceptance)
5. Break scope down into UoWs
6. Append 📋 PREFLIGHT + SHAPE REPORT to `BET-LOG.md`

## Output
PREFLIGHT REPORT + SHAPE REPORT
