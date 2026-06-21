"""
Net Buy Trend Strategy
----------------------
Logic:
  - Calculate daily net buying pressure (buys minus sells, approximated from OHLCV)
  - If net buy pressure increases for 3 consecutive days  → BUY on day 3
  - Sell when net buy reverses after a run (momentum exhaustion)

Net buy pressure per day:
  buy_vol  = ((close - low)  / (high - low)) * volume
  sell_vol = ((high - close) / (high - low)) * volume
  net_buy  = buy_vol - sell_vol   (positive = buyers winning)
"""

from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import numpy as np
import yfinance as yf

TOP_N_RESULTS = 20        # show top N buy/sell signals from full scan
PARALLEL_WORKERS = 30     # concurrent yfinance downloads


@dataclass
class NetBuySignal:
    ticker: str
    action: str           # "BUY" | "SELL" | "HOLD"
    price: float
    net_buy_d1: float     # net buy 3 days ago
    net_buy_d2: float     # net buy 2 days ago
    net_buy_d3: float     # net buy yesterday (most recent)
    trend_days: int       # consecutive days of increasing net buy
    obv_slope: float      # OBV 5-day slope (positive = rising)
    reason: str
    score: float = field(default=0.0)   # ranking score (higher = stronger signal)


def _fetch_daily(ticker: str, period: str = "30d") -> pd.DataFrame:
    df = yf.download(ticker, period=period, interval="1d",
                     auto_adjust=True, progress=False)
    if df.empty:
        raise ValueError(f"No data for {ticker}")
    df.columns = [c.lower() if isinstance(c, str) else c[0].lower() for c in df.columns]
    return df


def _net_buy_series(df: pd.DataFrame) -> pd.Series:
    spread = (df["high"] - df["low"]).replace(0, np.nan)
    buy_vol  = ((df["close"] - df["low"])  / spread) * df["volume"]
    sell_vol = ((df["high"]  - df["close"]) / spread) * df["volume"]
    return (buy_vol - sell_vol).fillna(0)


def _obv(df: pd.DataFrame) -> pd.Series:
    direction = np.sign(df["close"].diff().fillna(0))
    return (direction * df["volume"]).cumsum()


def _consecutive_increasing(series: pd.Series, n: int = 5) -> int:
    vals = series.iloc[-n:].values
    count = 0
    for i in range(len(vals) - 1, 0, -1):
        if vals[i] > vals[i - 1]:
            count += 1
        else:
            break
    return count


def _score(sig: NetBuySignal) -> float:
    """
    Rank buy signals by quality:
      - longer streak = better
      - faster OBV growth = better
      - larger net buy D3 vs D1 = better acceleration
    """
    if sig.action == "BUY":
        acceleration = (sig.net_buy_d3 - sig.net_buy_d1) / (abs(sig.net_buy_d1) + 1)
        return sig.trend_days * 10 + (sig.obv_slope / 1e6) + acceleration / 1e6
    if sig.action == "SELL":
        reversal = (sig.net_buy_d2 - sig.net_buy_d3) / (abs(sig.net_buy_d2) + 1)
        return reversal / 1e6
    return 0.0


def analyze_net_buy(ticker: str) -> NetBuySignal:
    df = _fetch_daily(ticker)
    net_buy = _net_buy_series(df)
    obv     = _obv(df)

    nb = net_buy.iloc[-3:].values
    if len(nb) < 3:
        raise ValueError("Not enough data")
    d1, d2, d3 = float(nb[0]), float(nb[1]), float(nb[2])

    trend_days = _consecutive_increasing(net_buy, n=5)

    obv_vals  = obv.iloc[-5:].values
    obv_slope = float(np.polyfit(range(len(obv_vals)), obv_vals, 1)[0])

    price = float(df["close"].iloc[-1])

    # ── BUY ──────────────────────────────────────────────────────────────────
    if trend_days >= 3 and obv_slope > 0 and d1 < d2 < d3:
        reason = (
            f"Net buy ↑ {trend_days}d streak: "
            f"{d1/1e6:.2f}M → {d2/1e6:.2f}M → {d3/1e6:.2f}M | OBV +{obv_slope/1e6:.1f}M/day"
        )
        sig = NetBuySignal(ticker, "BUY", price, d1, d2, d3, trend_days, obv_slope, reason)
        sig.score = _score(sig)
        return sig

    # ── SELL ─────────────────────────────────────────────────────────────────
    if trend_days == 0 and d2 > d3 and obv_slope < 0:
        reason = (
            f"Net buy reversed: {d2/1e6:.2f}M → {d3/1e6:.2f}M | OBV {obv_slope/1e6:.1f}M/day"
        )
        sig = NetBuySignal(ticker, "SELL", price, d1, d2, d3, trend_days, obv_slope, reason)
        sig.score = _score(sig)
        return sig

    reason = f"{trend_days}d streak | latest {d3/1e6:.2f}M | OBV {obv_slope/1e6:.1f}M/day"
    return NetBuySignal(ticker, "HOLD", price, d1, d2, d3, trend_days, obv_slope, reason, score=0.0)


def run_net_buy_scan(
    tickers: list[str],
    workers: int = PARALLEL_WORKERS,
    top_n: int = TOP_N_RESULTS,
    verbose: bool = True,
) -> list[NetBuySignal]:
    """
    Scan *tickers* in parallel. Returns top_n BUY signals (ranked) +
    all SELL signals + a sample of HOLDs.
    """
    total = len(tickers)
    results: list[NetBuySignal] = []
    errors = 0

    if verbose:
        print(f"  Scanning {total} tickers with {workers} parallel workers...")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(analyze_net_buy, t): t for t in tickers}
        done = 0
        for future in as_completed(futures):
            done += 1
            if verbose and done % 50 == 0:
                print(f"  [{done}/{total}] scanned...", flush=True)
            try:
                results.append(future.result())
            except Exception:
                errors += 1

    if verbose:
        buys  = sum(1 for r in results if r.action == "BUY")
        sells = sum(1 for r in results if r.action == "SELL")
        print(f"  Done. {len(results)} scanned | {buys} BUY | {sells} SELL | {errors} errors")

    buys  = sorted([r for r in results if r.action == "BUY"],  key=lambda x: x.score, reverse=True)
    sells = sorted([r for r in results if r.action == "SELL"], key=lambda x: x.score, reverse=True)
    holds = [r for r in results if r.action == "HOLD"]

    return buys[:top_n] + sells + holds[:5]
