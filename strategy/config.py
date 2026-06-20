"""Trading strategy configuration for a $50 Robinhood agentic account."""

# ── Capital & position sizing ─────────────────────────────────────────────────
TOTAL_CAPITAL = 50.0          # USD funded in agentic account
CASH_BUFFER = 10.0             # always keep this much uninvested
TRADEABLE_CAPITAL = TOTAL_CAPITAL - CASH_BUFFER  # $40 available for trading

MAX_POSITION_SIZE = 15.0       # max dollars per position
MIN_TRADE_SIZE = 5.0           # don't place orders smaller than this
MAX_OPEN_POSITIONS = 2         # max concurrent holdings

# ── Watchlist ─────────────────────────────────────────────────────────────────
# Liquid, fractional-share eligible; blend of ETFs + blue-chips
WATCHLIST = ["SPY", "QQQ", "AAPL", "MSFT", "NVDA"]

# ── RSI parameters ───────────────────────────────────────────────────────────
RSI_PERIOD = 14
RSI_OVERSOLD = 35              # buy signal threshold
RSI_OVERBOUGHT = 65            # sell signal threshold

# ── EMA parameters ───────────────────────────────────────────────────────────
EMA_FAST = 9
EMA_SLOW = 21

# ── ATR parameters ───────────────────────────────────────────────────────────
ATR_PERIOD = 14
ATR_VOLATILITY_THRESHOLD = 0.03  # skip trade if ATR/price > 3% (too volatile)

# ── Risk management ───────────────────────────────────────────────────────────
STOP_LOSS_PCT = 0.05           # 5% below entry → exit
TAKE_PROFIT_PCT = 0.10         # 10% above entry → exit
MIN_SIGNALS_TO_TRADE = 2       # need at least 2/3 indicators aligned

# ── Market data ───────────────────────────────────────────────────────────────
DATA_PERIOD = "60d"            # lookback window for indicator warmup
DATA_INTERVAL = "1h"           # 1-hour bars
VOLUME_LOOKBACK = 20           # days for avg-volume filter

# ── Market hours (ET) ─────────────────────────────────────────────────────────
MARKET_OPEN_HOUR = 9
MARKET_OPEN_MINUTE = 30
MARKET_CLOSE_HOUR = 16
AVOID_FIRST_MINUTES = 30       # skip first 30 min (volatile open)
AVOID_LAST_MINUTES = 30        # skip last 30 min (volatile close)
