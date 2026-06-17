"""Technical indicators: RSI, VWAP, EMA, ATR."""

import pandas as pd
import numpy as np
from .config import RSI_PERIOD, EMA_FAST, EMA_SLOW, ATR_PERIOD


def rsi(close: pd.Series, period: int = RSI_PERIOD) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def vwap(df: pd.DataFrame) -> pd.Series:
    """Intraday VWAP — resets each calendar day."""
    typical = (df["high"] + df["low"] + df["close"]) / 3
    dollar_vol = typical * df["volume"]
    # group by date
    df2 = df.copy()
    df2["date"] = df2.index.normalize()
    df2["cum_dv"] = dollar_vol.groupby(df2["date"]).cumsum()
    df2["cum_vol"] = df2["volume"].groupby(df2["date"]).cumsum()
    return df2["cum_dv"] / df2["cum_vol"]


def atr(df: pd.DataFrame, period: int = ATR_PERIOD) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    prev_c = c.shift(1)
    tr = pd.concat([h - l, (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()


def compute_all(df: pd.DataFrame) -> pd.DataFrame:
    """Attach RSI, EMA9, EMA21, VWAP, ATR columns to *df* (in-place copy)."""
    out = df.copy()
    out["rsi"] = rsi(out["close"])
    out["ema_fast"] = ema(out["close"], EMA_FAST)
    out["ema_slow"] = ema(out["close"], EMA_SLOW)
    out["vwap"] = vwap(out)
    out["atr"] = atr(out)
    out["atr_pct"] = out["atr"] / out["close"]
    return out
