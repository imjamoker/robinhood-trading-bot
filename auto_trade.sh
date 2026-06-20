#!/usr/bin/env bash
# Automated trading cycle — runs via LaunchAgent every hour during market hours.
# Uses caffeinate to prevent Mac sleeping mid-run.
# Uses claude -p with Robinhood MCP (already authenticated locally).

cd /Users/anuragpampati/robinhood

LOGFILE="logs/auto_run.log"
TRADELOG="logs/trade_log.md"
PY="/Users/anuragpampati/anaconda3/bin/python3"
CLAUDE="/Users/anuragpampati/.local/bin/claude"
TS=$(date '+%Y-%m-%d %H:%M:%S')

# Prevent Mac from sleeping during this run
caffeinate -i -t 300 &
CAFPID=$!

echo "" >> "$LOGFILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >> "$LOGFILE"
echo "[$TS] Starting trading cycle" >> "$LOGFILE"

# ── Step 1: Generate signals ──────────────────────────────────────────────────
$PY -m strategy.run 2>/dev/null >> "$LOGFILE"
echo "[$TS] Signals generated." >> "$LOGFILE"

# ── Step 2: Claude executes trades via Robinhood MCP ─────────────────────────
cat > /tmp/rh_prompt.txt << 'EOF'
You are an automated trading agent. The signal file is at logs/latest_signals.json.

Do the following in order:
1. Run: cat logs/latest_signals.json
2. If market_open is false: print "MARKET_CLOSED" and stop.
3. Use the robinhood-trading MCP tools to get buying power and open positions.
Maximum buys per run: 2.
Keep a running count of buys placed.
Once 2 buys have been executed, do not place any additional buy orders.
4. For each entry in net_buy_buy_signals where trend_days >= 3:
   - Skip if you already hold that ticker
   - Skip if buying power after trade would be below $10
   - Place a buy order for $15 (if score > 30) or $10 (otherwise)
   - Print: BOUGHT <ticker> $<amount> @ $<price>
5. For each entry in rsi_signals where action=BUY and confidence >= 2:
Skip all RSI buys if the maximum buys per run has already been reached.
   - Same skip rules as above
   - Place a buy order for $10
   - Print: BOUGHT <ticker> $<amount> @ $<price>
6. For each position you hold, check if net_buy_sell_signals or rsi_signals has action=SELL:
   - Sell the full position
   - Print: SOLD <ticker> <shares> @ $<price>
7. Check stop-loss (-5% from entry) and take-profit (+10% from entry) on all held positions.
   - Print: STOP_LOSS <ticker> or TAKE_PROFIT <ticker>
8. Print a one-line summary starting with "SUMMARY:" of all actions taken.

Only print actions you actually took. Do not write to any files.
EOF

echo "[$TS] Running Claude trade executor..." >> "$LOGFILE"
CLAUDE_OUTPUT=$(cat /tmp/rh_prompt.txt | "$CLAUDE" -p \
    --allowedTools "mcp__robinhood-trading__get_accounts,mcp__robinhood-trading__get_portfolio,mcp__robinhood-trading__get_equity_positions,mcp__robinhood-trading__get_equity_orders,mcp__robinhood-trading__get_equity_quotes,mcp__robinhood-trading__get_equity_tradability,mcp__robinhood-trading__place_equity_order,mcp__robinhood-trading__review_equity_order,mcp__robinhood-trading__cancel_equity_order,Bash" \
    2>/dev/null)

echo "$CLAUDE_OUTPUT" >> "$LOGFILE"

# ── Step 3: Write to trade log ────────────────────────────────────────────────
echo "" >> "$TRADELOG"
echo "## $TS" >> "$TRADELOG"

if echo "$CLAUDE_OUTPUT" | grep -q "MARKET_CLOSED"; then
    echo "- Market closed — no trades placed." >> "$TRADELOG"
else
    echo "$CLAUDE_OUTPUT" | grep -E "^(BOUGHT|SOLD|STOP_LOSS|TAKE_PROFIT|SUMMARY)" | while read -r line; do
        echo "- $line" >> "$TRADELOG"
    done
fi

# ── Step 4: Push updated logs to GitHub (dashboard updates automatically) ─────
cp logs/latest_signals.json docs/signals.json 2>/dev/null
cp logs/trade_log.md docs/trade_log.md 2>/dev/null
git add logs/trade_log.md logs/latest_signals.json docs/ 2>/dev/null
git diff --staged --quiet 2>/dev/null || \
    git commit -m "chore: trading cycle $TS" 2>/dev/null && \
    git push 2>/dev/null &

echo "[$TS] Cycle complete." >> "$LOGFILE"

# Stop caffeinate
kill $CAFPID 2>/dev/null
rm -f /tmp/rh_prompt.txt
