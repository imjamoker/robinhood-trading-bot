"""Generate BUY / SELL / HOLD signals from indicator data."""

from dataclasses import dataclass
import pandas as pd
from .config import (
    RSI_OVERSOLD, RSI_OVERBOUGHT,
    ATR_VOLATILITY_THRESHOLD, MIN_SIGNALS_TO_TRADE,
)


@dataclass
class Signal:
    ticker: str
    action: str          # "BUY" | "SELL" | "HOLD"
    price: float
    rsi: float
    ema_trend: str       # "BULLISH" | "BEARISH" | "NEUTRAL"
    vwap_bias: str       # "BELOW" | "ABOVE" | "AT"
    confidence: int      # 0-3 (number of aligned indicators)
    atr_pct: float
    reason: str


def _ema_trend(row: pd.Series) -> str:
    if row["ema_fast"] > row["ema_slow"] * 1.001:
        return "BULLISH"
    if row["ema_fast"] < row["ema_slow"] * 0.999:
        return "BEARISH"
    return "NEUTRAL"


def _vwap_bias(row: pd.Series) -> str:
    ratio = row["close"] / row["vwap"]
    if ratio < 0.99:
        return "BELOW"
    if ratio > 1.01:
        return "ABOVE"
    return "AT"


def generate_signal(ticker: str, df: pd.DataFrame) -> Signal:
    """Produce a trading signal for *ticker* from its indicator DataFrame."""
    row = df.dropna(subset=["rsi", "ema_fast", "ema_slow", "vwap", "atr"]).iloc[-1]
    price = float(row["close"])
    rsi_val = float(row["rsi"])
    atr_pct = float(row["atr_pct"])
    trend = _ema_trend(row)
    bias = _vwap_bias(row)

    # Volatility gate — skip if market is too choppy
    if atr_pct > ATR_VOLATILITY_THRESHOLD:
        return Signal(ticker, "HOLD", price, rsi_val, trend, bias, 0, atr_pct,
                      f"ATR too high ({atr_pct:.1%}) — skipping")

    # ── BUY scoring ──────────────────────────────────────────────────────────
    buy_score = 0
    buy_reasons = []
    if rsi_val < RSI_OVERSOLD:
        buy_score += 1
        buy_reasons.append(f"RSI oversold ({rsi_val:.1f})")
    if bias == "BELOW":
        buy_score += 1
        buy_reasons.append("price below VWAP")
    if trend == "BULLISH":
        buy_score += 1
        buy_reasons.append("EMA bullish crossover")

    # ── SELL scoring ─────────────────────────────────────────────────────────
    sell_score = 0
    sell_reasons = []
    if rsi_val > RSI_OVERBOUGHT:
        sell_score += 1
        sell_reasons.append(f"RSI overbought ({rsi_val:.1f})")
    if bias == "ABOVE":
        sell_score += 1
        sell_reasons.append("price above VWAP")
    if trend == "BEARISH":
        sell_score += 1
        sell_reasons.append("EMA bearish crossover")

    if buy_score >= MIN_SIGNALS_TO_TRADE and buy_score > sell_score:
        return Signal(ticker, "BUY", price, rsi_val, trend, bias,
                      buy_score, atr_pct, " | ".join(buy_reasons))

    if sell_score >= MIN_SIGNALS_TO_TRADE and sell_score > buy_score:
        return Signal(ticker, "SELL", price, rsi_val, trend, bias,
                      sell_score, atr_pct, " | ".join(sell_reasons))

    reason = f"RSI={rsi_val:.1f}, trend={trend}, VWAP={bias}"
    return Signal(ticker, "HOLD", price, rsi_val, trend, bias, 0, atr_pct, reason)
