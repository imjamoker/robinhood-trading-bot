"""
Main signal runner — scans full S&P 500 + NASDAQ 100 universe.

Usage:
    python -m strategy.run            # full universe scan
    python -m strategy.run --quick   # watchlist only (5 tickers, fast)
"""

import json
import sys
from datetime import datetime, timezone
from tabulate import tabulate

from .market_data import fetch_all_watchlist, is_market_open
from .indicators import compute_all
from .signals import generate_signal
from .net_buy import run_net_buy_scan, NetBuySignal
from .risk import risk_summary
from .universe import full_universe
from .config import WATCHLIST, TOTAL_CAPITAL, CASH_BUFFER

QUICK_MODE = "--quick" in sys.argv


def _merged_action(rsi_action: str, nb_action: str) -> str:
    if rsi_action == nb_action:
        return rsi_action
    if rsi_action != "HOLD":
        return rsi_action
    return nb_action


def run_analysis() -> dict:
    market_open = is_market_open()
    timestamp = datetime.now(timezone.utc).isoformat()
    mode = "QUICK (watchlist only)" if QUICK_MODE else "FULL UNIVERSE (S&P 500 + NASDAQ 100)"

    print(f"\n{'='*65}")
    print(f"  Robinhood Agentic Trading Signal Report")
    print(f"  {timestamp}")
    print(f"  Mode        : {mode}")
    print(f"  Market open : {market_open}")
    print(f"{'='*65}\n")

    if not market_open:
        print("[INFO] Market is currently closed. No trades will be placed.\n")

    # ── Determine universe ────────────────────────────────────────────────────
    if QUICK_MODE:
        universe = WATCHLIST
        print(f"[1/4] Using watchlist ({len(universe)} tickers)...")
    else:
        print("[1/4] Fetching full stock universe (S&P 500 + NASDAQ 100)...")
        universe = full_universe()
        print(f"      {len(universe)} tickers loaded.\n")

    # ── Strategy 1: RSI + VWAP + EMA on watchlist ────────────────────────────
    print("[2/4] Computing RSI / VWAP / EMA on watchlist...")
    data_map = fetch_all_watchlist(WATCHLIST)
    rsi_signals = {}
    for ticker, df in data_map.items():
        try:
            df_ind = compute_all(df)
            rsi_signals[ticker] = generate_signal(ticker, df_ind)
        except Exception as exc:
            print(f"  [WARN] {ticker}: {exc}")

    # ── Strategy 2: Net Buy Trend scan on full universe ───────────────────────
    print(f"[3/4] Scanning 3-day net buy trends across {len(universe)} tickers...")
    nb_results = run_net_buy_scan(universe, verbose=True)
    nb_by_ticker = {s.ticker: s for s in nb_results}

    print("\n[4/4] Building report...\n")

    # ── Table 1: RSI signals on watchlist ─────────────────────────────────────
    print("STRATEGY 1 — RSI + VWAP + EMA  [watchlist]")
    rows1 = []
    for s in rsi_signals.values():
        rows1.append([s.ticker, s.action, f"${s.price:.2f}",
                      f"{s.rsi:.1f}", s.ema_trend, s.vwap_bias,
                      f"{s.confidence}/3", f"{s.atr_pct:.1%}"])
    print(tabulate(rows1,
                   headers=["Ticker", "Action", "Price", "RSI", "EMA", "VWAP", "Conf", "ATR%"],
                   tablefmt="rounded_outline"))

    # ── Table 2: Top Net Buy signals from full universe ───────────────────────
    buy_signals  = [s for s in nb_results if s.action == "BUY"]
    sell_signals = [s for s in nb_results if s.action == "SELL"]

    print(f"\nSTRATEGY 2 — 3-Day Net Buy Trend  [{len(universe)} stocks scanned]")
    print(f"  Top BUY candidates ({len(buy_signals)} found, showing top 15):")
    rows2 = []
    for s in buy_signals[:15]:
        rows2.append([
            s.ticker, f"${s.price:.2f}",
            f"{s.net_buy_d1/1e6:.1f}M",
            f"{s.net_buy_d2/1e6:.1f}M",
            f"{s.net_buy_d3/1e6:.1f}M",
            f"{s.trend_days}d",
            "↑" if s.obv_slope > 0 else "↓",
            f"{s.score:.1f}",
        ])
    print(tabulate(rows2,
                   headers=["Ticker", "Price", "NetBuy D-2", "NetBuy D-1", "NetBuy D0", "Streak", "OBV", "Score"],
                   tablefmt="rounded_outline"))

    if sell_signals:
        print(f"\n  SELL signals from full universe ({len(sell_signals)} found):")
        rows3 = []
        for s in sell_signals[:10]:
            rows3.append([
                s.ticker, f"${s.price:.2f}",
                f"{s.net_buy_d2/1e6:.1f}M → {s.net_buy_d3/1e6:.1f}M",
                "↓", f"{s.score:.1f}",
            ])
        print(tabulate(rows3,
                       headers=["Ticker", "Price", "NetBuy D-1 → D0", "OBV", "Score"],
                       tablefmt="rounded_outline"))

    # ── Combined actionable signals ───────────────────────────────────────────
    print("\n── COMBINED Actionable Signals ──")
    actionable = []
    all_tickers = set(rsi_signals) | set(nb_by_ticker)
    for ticker in all_tickers:
        rs = rsi_signals.get(ticker)
        nb = nb_by_ticker.get(ticker)
        rsi_act = rs.action if rs else "HOLD"
        nb_act  = nb.action if nb else "HOLD"
        merged  = _merged_action(rsi_act, nb_act)
        both_agree = rsi_act == nb_act and rsi_act != "HOLD"
        if merged in ("BUY", "SELL"):
            price = rs.price if rs else (nb.price if nb else 0)
            tag = "STRONG" if both_agree else "MODERATE"
            actionable.append((ticker, merged, price, tag, rs, nb))

    # Also add pure net-buy signals not in watchlist
    for s in buy_signals[:5]:
        if s.ticker not in rsi_signals:
            actionable.append((s.ticker, "BUY", s.price, "NET-BUY", None, s))

    if not actionable:
        print("  No actionable signals right now. HOLD all positions.")
    else:
        for ticker, action, price, tag, rs, nb in actionable:
            print(f"\n  [{tag}] {action} {ticker} @ ${price:.2f}")
            if rs and rs.action == action:
                print(f"    RSI strategy : {rs.reason}")
            if nb and nb.action == action:
                print(f"    Net buy trend: {nb.reason}")
            if action == "BUY":
                dollar_amt = 20.0 if tag == "STRONG" else 15.0
                rr = risk_summary(price, dollar_amt)
                print(f"    Amount       : ${dollar_amt}  |  Stop: ${rr['stop_loss']:.2f}  |  Target: ${rr['take_profit']:.2f}  |  R:R 1:{rr['risk_reward']}")

    # ── Save JSON ─────────────────────────────────────────────────────────────
    report = {
        "timestamp": timestamp,
        "mode": "quick" if QUICK_MODE else "full_universe",
        "universe_size": len(universe),
        "market_open": market_open,
        "rsi_signals": [
            {"ticker": s.ticker, "action": s.action, "price": s.price,
             "rsi": round(s.rsi, 2), "ema_trend": s.ema_trend,
             "vwap_bias": s.vwap_bias, "confidence": s.confidence,
             "atr_pct": round(s.atr_pct, 4), "reason": s.reason}
            for s in rsi_signals.values()
        ],
        "net_buy_buy_signals": [
            {"ticker": s.ticker, "price": s.price,
             "net_buy_d1": round(s.net_buy_d1), "net_buy_d2": round(s.net_buy_d2),
             "net_buy_d3": round(s.net_buy_d3), "trend_days": s.trend_days,
             "obv_slope": round(s.obv_slope), "score": round(s.score, 2),
             "reason": s.reason}
            for s in buy_signals[:20]
        ],
        "net_buy_sell_signals": [
            {"ticker": s.ticker, "price": s.price,
             "net_buy_d2": round(s.net_buy_d2), "net_buy_d3": round(s.net_buy_d3),
             "obv_slope": round(s.obv_slope), "score": round(s.score, 2),
             "reason": s.reason}
            for s in sell_signals[:10]
        ],
    }

    with open("logs/latest_signals.json", "w") as f:
        json.dump(report, f, indent=2)
    print("\n[OK] Full report saved → logs/latest_signals.json")

    print("\n── CLAUDE AGENT INSTRUCTIONS ──")
    print("  STRONG BUY  → buy up to $20 (both strategies agree)")
    print("  NET-BUY     → buy up to $15 (net buy trend only, strong streak)")
    print("  MODERATE BUY→ buy up to $15 (one strategy)")
    print("  Any SELL on a held position → sell full position immediately")
    print("  DO NOT trade if market_open is False.\n")

    return report


if __name__ == "__main__":
    run_analysis()
