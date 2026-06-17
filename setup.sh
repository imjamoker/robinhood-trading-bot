#!/usr/bin/env bash
set -e

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║  Robinhood Agentic Trading — Setup               ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# ── 1. Python dependencies ────────────────────────────────────────────────────
echo "[1/3] Installing Python dependencies..."
pip3 install -q -r requirements.txt
echo "      Done."

# ── 2. Add Robinhood MCP to Claude Code ──────────────────────────────────────
echo ""
echo "[2/3] Registering Robinhood MCP server with Claude Code..."
if claude mcp list 2>/dev/null | grep -q "robinhood-trading"; then
    echo "      robinhood-trading MCP already registered."
else
    claude mcp add robinhood-trading --transport http https://agent.robinhood.com/mcp/trading
    echo "      Registered: robinhood-trading → https://agent.robinhood.com/mcp/trading"
fi

# ── 3. Smoke test ─────────────────────────────────────────────────────────────
echo ""
echo "[3/3] Running smoke test (fetches SPY data, checks indicators)..."
python3 - <<'PYEOF'
import sys
sys.path.insert(0, '.')
from strategy.market_data import fetch_ohlcv, is_market_open
from strategy.indicators import compute_all
from strategy.signals import generate_signal

df = fetch_ohlcv("SPY", period="30d", interval="1h")
df_ind = compute_all(df)
sig = generate_signal("SPY", df_ind)
print(f"  SPY signal: {sig.action}  RSI={sig.rsi:.1f}  Confidence={sig.confidence}/3")
print(f"  Market open: {is_market_open()}")
print("  Smoke test PASSED ✓")
PYEOF

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║  Setup complete!                                 ║"
echo "║                                                  ║"
echo "║  Next steps:                                     ║"
echo "║  1. Open Robinhood → create Agentic sub-account  ║"
echo "║  2. Fund it with \$100                            ║"
echo "║  3. In Claude Code: /mcp → authenticate RH       ║"
echo "║  4. Run: python -m strategy.run                  ║"
echo "║  5. Claude will execute trades from signals      ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
