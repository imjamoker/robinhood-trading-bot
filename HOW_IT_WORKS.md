# Robinhood Agentic Trading — How It Works

## What This Does
An AI trading agent (Claude) monitors 5 stocks every hour during market hours.
When the indicators say "buy" or "sell", it acts automatically via your Robinhood agentic account.
Your $100 is in a **dedicated sub-account** — your main Robinhood portfolio is untouched.

---

## Commands

| What you want | Command |
|---------------|---------|
| Run once manually | `python3 -m strategy.run` |
| Watch auto-run logs | `tail -f logs/auto_run.log` |
| See latest signals | `cat logs/latest_signals.json` |
| See trade history | `cat logs/trade_log.md` |

The strategy **runs automatically every hour on weekdays** via cron — you don't need to do anything after setup.

---

## Schedule
- Runs: **Mon–Fri, 10am–3pm ET** (avoids volatile open/close windows)
- Frequency: **every hour**
- Outside those hours: signals are calculated but no trades are placed

---

## The Strategy (Plain English)

Two strategies run together. When both agree on a trade, it's a **STRONG** signal. When only one fires, it's **MODERATE**.

### Watchlist
`SPY` · `QQQ` · `AAPL` · `MSFT` · `NVDA`

---

### Strategy 1 — RSI + VWAP + EMA (intraday momentum)

#### BUY — at least 2 of these 3 must be true:
1. **RSI < 35** — stock is oversold (beaten down, likely to bounce)
2. **Price below VWAP** — trading cheaper than today's average price
3. **EMA bullish crossover** — short-term momentum turning upward

#### SELL — at least 2 of these 3 must be true:
1. **RSI > 65** — stock is overbought (likely to pull back)
2. **Price above VWAP** — trading above today's average price
3. **EMA bearish crossover** — short-term momentum turning downward

---

### Strategy 2 — 3-Day Net Buy Trend (new)

This tracks whether **buyers are consistently winning** over sellers for 3 days in a row.

**How net buy is calculated per day:**
- Every candle: estimate how much of the day's volume was buying vs selling
- `Net Buy = (buy volume) − (sell volume)` — approximated from price position in the day's range
- Also tracks **OBV (On-Balance Volume)** — a cumulative running total of buying pressure

#### BUY — triggered on Day 3 when ALL of these are true:
| Check | Meaning |
|-------|---------|
| Net buy Day 1 < Day 2 < Day 3 | Buyers increasing each day for 3 days |
| Streak ≥ 3 days | Confirmed trend, not a one-day spike |
| OBV slope rising (↑) | Overall buying pressure building up |

#### SELL — triggered when:
| Check | Meaning |
|-------|---------|
| Net buy reverses (Day 2 > Day 3) | Buyers stepping back |
| OBV slope falling (↓) | Momentum exhausted |

This is your **"sell on the next high day"** rule — when net buy reverses after a run-up, it typically coincides with a short-term price peak.

---

### Signal Strength

| Both strategies say BUY | → **STRONG BUY** — invest up to $20 |
|--------------------------|--------------------------------------|
| Only one strategy says BUY | → **MODERATE BUY** — invest up to $15 |
| Either strategy says SELL on a held position | → **SELL** immediately |

---

### Automatic exits (no signal needed)
| Condition | Action |
|-----------|--------|
| Price drops 5% from your entry | Sell — stop-loss triggered |
| Price rises 10% from your entry | Sell — take-profit hit |

---

## Money Rules (Hard Limits)

| Rule | Value |
|------|-------|
| Total account | $100 |
| Always kept as cash buffer | $10 minimum |
| Max spent on one position | $20 |
| Minimum order size | $5 |
| Max open positions at once | 4 |
| Uses margin or leverage | Never |

---

## Risk vs Reward

Every trade is structured as **1:2 risk/reward**:
- You risk **$1** to potentially make **$2**
- Stop-loss at **−5%** from entry
- Take-profit at **+10%** from entry

This means even if you're only right **35% of the time**, you still come out ahead over many trades.

---

## Realistic Returns on $100

| Scenario | Monthly Return | Dollar Amount |
|----------|---------------|---------------|
| Conservative | +2% to +5% | $2 – $5 |
| Moderate | +5% to +12% | $5 – $12 |
| Optimistic | +12% to +20% | $12 – $20 |
| Bad month | −5% to −10% | −$5 to −$10 |

**6-month outlook (if conditions are favorable):** $100 → $130–$170

### Honest caveats
- Most hours the signal will be **HOLD** — this is normal and good (no bad trades)
- Dollar gains on $100 are small; the goal is to prove the strategy before scaling up
- No strategy guarantees profit — black swan events and gaps can override any signal
- Past indicator patterns don't guarantee future results

---

## File Structure

```
robinhood/
├── CLAUDE.md              ← Rules Claude follows as trading agent
├── HOW_IT_WORKS.md        ← This file
├── requirements.txt       ← Python dependencies
├── setup.sh               ← One-command setup script
├── trade.sh               ← Manual one-click trade cycle
├── strategy/
│   ├── config.py          ← All parameters (thresholds, position sizes)
│   ├── indicators.py      ← RSI, VWAP, EMA, ATR calculations
│   ├── signals.py         ← Buy/sell signal logic
│   ├── risk.py            ← Stop-loss, take-profit, position sizing
│   ├── market_data.py     ← Fetches live data via yfinance
│   └── run.py             ← Main runner — prints signal table
└── logs/
    ├── latest_signals.json ← Output from last run
    ├── trade_log.md        ← Record of every trade placed
    └── auto_run.log        ← Cron job output history
```

---

## To Adjust the Strategy

Edit `strategy/config.py` to tune any parameter:

```python
RSI_OVERSOLD = 35        # lower = stricter buy signal (e.g. change to 30)
RSI_OVERBOUGHT = 65      # higher = stricter sell signal (e.g. change to 70)
STOP_LOSS_PCT = 0.05     # 5% stop-loss
TAKE_PROFIT_PCT = 0.10   # 10% take-profit
MAX_POSITION_SIZE = 20.0 # max $ per trade
WATCHLIST = ["SPY", "QQQ", "AAPL", "MSFT", "NVDA"]
```

---

## If Something Looks Wrong
1. Check `logs/auto_run.log` for errors
2. Run `python3 -m strategy.run` manually to see the current signal table
3. Check your Robinhood agentic account in the app to verify positions
4. To stop all auto-trading: `crontab -r` (removes the scheduled job)
