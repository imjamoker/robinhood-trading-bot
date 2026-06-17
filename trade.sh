#!/usr/bin/env bash
# Run one trading cycle. Safe to call any time — skips trades if market closed.
cd "$(dirname "$0")"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Running strategy cycle..."
python3 -m strategy.run 2>/dev/null
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Cycle complete. See logs/latest_signals.json"
