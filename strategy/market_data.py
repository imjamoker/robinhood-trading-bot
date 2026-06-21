"""Fetch OHLCV market data via yfinance."""

import yfinance as yf
import pandas as pd
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Optional
from .config import DATA_PERIOD, DATA_INTERVAL, WATCHLIST

try:
    import exchange_calendars as xcals
except ImportError:  # pragma: no cover - optional runtime dependency
    xcals = None


def fetch_ohlcv(ticker: str, period: str = DATA_PERIOD, interval: str = DATA_INTERVAL) -> pd.DataFrame:
    """Return OHLCV DataFrame for *ticker*. Raises on empty data."""
    df = yf.download(ticker, period=period, interval=interval,
                     auto_adjust=True, progress=False)
    if df.empty:
        raise ValueError(f"No data returned for {ticker}")
    df.index = pd.to_datetime(df.index, utc=True)
    df.columns = [c.lower() if isinstance(c, str) else c[0].lower() for c in df.columns]
    return df


def fetch_all_watchlist(watchlist: list[str] = WATCHLIST) -> dict[str, pd.DataFrame]:
    """Fetch OHLCV for every ticker in *watchlist*. Skips failures."""
    result = {}
    for ticker in watchlist:
        try:
            result[ticker] = fetch_ohlcv(ticker)
        except Exception as exc:
            print(f"[WARN] {ticker}: {exc}")
    return result


def is_market_open() -> bool:
    """True if NYSE is currently open."""
    now = datetime.now(timezone.utc)
    if xcals is not None:
        calendar = xcals.get_calendar("XNYS")
        return bool(calendar.is_open_on_minute(pd.Timestamp(now)))

    # Fallback uses timezone rules but does not know holidays or early closes.
    local = now.astimezone(ZoneInfo("America/New_York"))
    if local.weekday() >= 5:
        return False
    open_time = local.replace(hour=9, minute=30, second=0, microsecond=0)
    close_time = local.replace(hour=16, minute=0, second=0, microsecond=0)
    return open_time <= local <= close_time


def current_price(ticker: str) -> Optional[float]:
    """Return latest closing price for *ticker*."""
    df = fetch_ohlcv(ticker, period="5d", interval="1m")
    if df.empty:
        return None
    return float(df["close"].iloc[-1])
