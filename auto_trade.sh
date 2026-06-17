#!/usr/bin/env bash
# Fully automated trading cycle — runs every hour via cron.
# 1. Generates signals across all S&P 500 stocks
# 2. Claude reads signals + executes buy/sell via Robinhood MCP
# 3. Shell script handles all logging

cd /Users/anuragpampati/Desktop/Claude/robinhood

LOGFILE="logs/auto_run.log"
TRADELOG="logs/trade_log.md"
PY="/Users/anuragpampati/anaconda3/bin/python3"
TS=$(date '+%Y-%m-%d %H:%M:%S')

echo "" >> "$LOGFILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >> "$LOGFILE"
echo "[$TS] Starting trading cycle" >> "$LOGFILE"

# ── Step 1: Generate signals ──────────────────────────────────────────────────
$PY -m strategy.run 2>/dev/null >> "$LOGFILE"
echo "[$TS] Signals generated → logs/latest_signals.json" >> "$LOGFILE"

# ── Step 2: Claude executes trades via Robinhood MCP ─────────────────────────
cat > /tmp/rh_prompt.txt << 'EOF'
You are an automated trading agent. The signal file is at logs/latest_signals.json.

Do the following in order:
1. Run: cat logs/latest_signals.json
2. If market_open is false: print "MARKET_CLOSED" and stop.
3. Use the robinhood-trading MCP tools to:
   a. Get current account buying power
   b. Get current open positions
4. For each entry in net_buy_buy_signals where trend_days >= 3:
   - Skip if you already hold that ticker
   - Skip if buying power after trade would be below $10
   - Place a buy order for $20 (if score > 30) or $15 (otherwise)
   - Print: BOUGHT <ticker> $<amount> @ $<price>
5. For each entry in rsi_signals where action=BUY and confidence >= 2:
   - Same skip rules as above
   - Place a buy order for $15
   - Print: BOUGHT <ticker> $<amount> @ $<price>
6. For each position you hold, check if net_buy_sell_signals or rsi_signals has action=SELL for that ticker:
   - Sell the full position
   - Print: SOLD <ticker> <shares> @ $<price>
7. For each held position, check stop-loss (5% below entry) and take-profit (10% above entry):
   - Exit if either threshold is hit
   - Print: STOP_LOSS <ticker> or TAKE_PROFIT <ticker>
8. At the end print a one-line summary starting with "SUMMARY:" of all actions taken.

Only print actions you actually took. Do not write to any files.
EOF

echo "[$TS] Running Claude trade executor..." >> "$LOGFILE"
CLAUDE_OUTPUT=$(cat /tmp/rh_prompt.txt | claude -p \
  --allowedTools "mcp__robinhood-trading__get_account,mcp__robinhood-trading__get_positions,mcp__robinhood-trading__place_order,mcp__robinhood-trading__get_orders,Bash" \
  2>/dev/null)

echo "$CLAUDE_OUTPUT" >> "$LOGFILE"

# ── Step 3: Write to trade log ────────────────────────────────────────────────
echo "" >> "$TRADELOG"
echo "## $TS" >> "$TRADELOG"

if echo "$CLAUDE_OUTPUT" | grep -q "MARKET_CLOSED"; then
    echo "- Market closed — no trades placed." >> "$TRADELOG"
else
    SUMMARY=$(echo "$CLAUDE_OUTPUT" | grep "SUMMARY:")
    if [ -n "$SUMMARY" ]; then
        echo "- $SUMMARY" >> "$TRADELOG"
    fi
    # Log each individual action
    echo "$CLAUDE_OUTPUT" | grep -E "^(BOUGHT|SOLD|STOP_LOSS|TAKE_PROFIT)" | while read -r line; do
        echo "- $line" >> "$TRADELOG"
    done
fi

echo "[$TS] Cycle complete." >> "$LOGFILE"
rm -f /tmp/rh_prompt.txt
