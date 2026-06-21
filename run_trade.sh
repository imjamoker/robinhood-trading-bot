#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$BASE_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"
LOGFILE="logs/auto_run.log"
TRADELOG="logs/trade_log.md"
TS="$(date '+%Y-%m-%d %H:%M:%S')"

mkdir -p logs docs

{
  echo ""
  echo "--------------------------------"
  echo "[$TS] Starting trading cycle"
} >> "$LOGFILE"

"$PYTHON_BIN" -m strategy.run >> "$LOGFILE" 2>&1
echo "[$TS] Signals generated." >> "$LOGFILE"

"$PYTHON_BIN" -m strategy.execute "$@" >> "$LOGFILE" 2>&1
echo "[$TS] Execution finished." >> "$LOGFILE"

cp logs/latest_signals.json docs/signals.json 2>/dev/null || true
cp "$TRADELOG" docs/trade_log.md 2>/dev/null || true

echo "[$TS] Cycle complete." >> "$LOGFILE"
