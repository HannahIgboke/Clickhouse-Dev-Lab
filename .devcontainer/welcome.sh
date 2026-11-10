#!/usr/bin/env bash
# Runs every time a Codespace starts. Starts ClickHouse (idempotent) and prints
# a short "here is what to type" banner. It is safe to run repeatedly.
set -u

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)" || true

# Start ClickHouse and the local S3 stand-in if they are not already up.
if ! python -m chlab.cli status >/dev/null 2>&1 || ! curl -sf http://localhost:8123/ping >/dev/null 2>&1; then
  echo "Starting ClickHouse and the S3 stand-in (first run downloads the images)..."
  chlab up >/tmp/chlab-up.log 2>&1 || python -m chlab.cli up >/tmp/chlab-up.log 2>&1 || true
fi

cat <<'BANNER'

  ┌────────────────────────────────────────────────────────────────────┐
  │  ClickHouse Dev Lab is ready.                                        │
  │                                                                    │
  │  Next, in this terminal:                                           │
  │                                                                    │
  │      chlab list      the 36 tasks and your best scores               │
  │      chlab start 1   fresh data + the task brief, clock starts       │
  │      chlab client    clickhouse-client — work here, like the exam    │
  │      chlab check     grade yourself                                  │
  │                                                                    │
  │  Full walkthrough: docs/START-HERE.md                              │
  │  Stop this Codespace when you finish, to save your free hours.     │
  └────────────────────────────────────────────────────────────────────┘

BANNER