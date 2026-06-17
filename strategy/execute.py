"""
Trade executor — no Claude needed.
Uses robin_stocks to place orders directly on Robinhood.

Credentials come from environment variables (set as GitHub Secrets in CI):
  RH_USERNAME   Robinhood email
  RH_PASSWORD   Robinhood password
  RH_TOTP_SECRET  (optional) base32 MFA secret for auto-generating 2FA codes
"""

import os
import json
import time
from datetime import datetime, timezone

# ── Auth ──────────────────────────────────────────────────────────────────────
def _login():
    import robin_stocks.robinhood as r
    import base64, pickle, tempfile

    # Preferred: use pre-generated OAuth token bundle (no MFA needed)
    rh_token_b64 = os.environ.get("RH_TOKEN", "")
    if rh_token_b64:
        import base64, json as _json
        bundle = _json.loads(base64.b64decode(rh_token_b64).decode())
        # Inject token directly into robin_stocks session
        r.helper.set_login_state(True)
        r.helper.update_session("Authorization", f"Bearer {bundle['access_token']}")
        r.helper.set_output(bundle, output_format="data")
        return r

    # Fallback: TOTP-based login
    username = os.environ["RH_USERNAME"]
    password = os.environ["RH_PASSWORD"]
    totp_secret = os.environ.get("RH_TOTP_SECRET", "")
    if totp_secret:
        import pyotp
        mfa_code = pyotp.TOTP(totp_secret).now()
        r.login(username, password, mfa_code=mfa_code, store_session=False)
    else:
        r.login(username, password, store_session=False)
    return r


# ── Helpers ───────────────────────────────────────────────────────────────────
def _buying_power(r) -> float:
    profile = r.load_account_profile()
    return float(profile.get("buying_power", 0) or 0)


def _positions(r) -> dict[str, dict]:
    """Return {ticker: {quantity, average_buy_price}} for open positions."""
    positions = {}
    for p in r.get_open_stock_positions():
        qty = float(p.get("quantity", 0) or 0)
        if qty <= 0:
            continue
        instrument_url = p.get("instrument")
        try:
            info = r.get_instrument_by_url(instrument_url)
            ticker = info.get("symbol", "")
        except Exception:
            continue
        positions[ticker] = {
            "quantity": qty,
            "avg_cost": float(p.get("average_buy_price", 0) or 0),
        }
    return positions


def _current_price(r, ticker: str) -> float:
    quotes = r.get_latest_price(ticker)
    return float(quotes[0]) if quotes else 0.0


def _log(trade_log_path: str, line: str):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entry = f"\n## {ts}\n- {line}\n"
    with open(trade_log_path, "a") as f:
        f.write(entry)
    print(line)


# ── Main executor ─────────────────────────────────────────────────────────────
def execute(signals_path: str = "logs/latest_signals.json",
            trade_log_path: str = "logs/trade_log.md",
            dry_run: bool = False):

    with open(signals_path) as f:
        report = json.load(f)

    if not report.get("market_open", False):
        print("Market closed — no trades.")
        _log(trade_log_path, "Market closed — no trades placed.")
        return

    print("Logging into Robinhood...")
    r = _login()

    buying_power = _buying_power(r)
    held = _positions(r)
    CASH_BUFFER = 10.0
    actions = []

    print(f"Buying power: ${buying_power:.2f} | Held: {list(held.keys())}")

    # ── Check exits on held positions ─────────────────────────────────────────
    sell_tickers = {s["ticker"] for s in report.get("net_buy_sell_signals", [])}
    sell_tickers |= {s["ticker"] for s in report.get("rsi_signals", []) if s["action"] == "SELL"}

    for ticker, pos in held.items():
        price = _current_price(r, ticker)
        avg = pos["avg_cost"]
        qty = pos["quantity"]
        reason = None

        if avg > 0 and price <= avg * 0.95:
            reason = f"STOP_LOSS (price ${price:.2f} <= stop ${avg*0.95:.2f})"
        elif avg > 0 and price >= avg * 1.10:
            reason = f"TAKE_PROFIT (price ${price:.2f} >= target ${avg*1.10:.2f})"
        elif ticker in sell_tickers:
            reason = "SELL signal — net buy reversed"

        if reason:
            msg = f"SELL {ticker} {qty:.4f} shares @ ${price:.2f} | {reason}"
            print(msg)
            if not dry_run:
                r.order_sell_fractional_by_quantity(ticker, qty, timeInForce="gfd")
                time.sleep(1)
            _log(trade_log_path, msg)
            actions.append(msg)

    # ── Enter new positions ───────────────────────────────────────────────────
    buy_signals = sorted(
        report.get("net_buy_buy_signals", []),
        key=lambda x: x.get("score", 0), reverse=True
    )
    rsi_buys = [s for s in report.get("rsi_signals", []) if s["action"] == "BUY"]

    def try_buy(ticker: str, dollar_amount: float, reason: str):
        nonlocal buying_power
        if ticker in held:
            print(f"  Skip {ticker} — already held")
            return
        if buying_power - dollar_amount < CASH_BUFFER:
            print(f"  Skip {ticker} — not enough buying power (${buying_power:.2f})")
            return
        price = _current_price(r, ticker)
        if price <= 0:
            return
        msg = f"BUY {ticker} ${dollar_amount:.2f} @ ${price:.2f} | {reason}"
        print(msg)
        if not dry_run:
            r.order_buy_fractional_by_price(ticker, dollar_amount, timeInForce="gfd")
            time.sleep(1)
        buying_power -= dollar_amount
        held[ticker] = {"quantity": dollar_amount / price, "avg_cost": price}
        _log(trade_log_path, msg)
        actions.append(msg)

    # Net buy signals (strongest first)
    for sig in buy_signals[:5]:
        amount = 20.0 if sig.get("score", 0) > 30 else 15.0
        try_buy(sig["ticker"], amount, f"Net buy {sig['trend_days']}d streak | score {sig.get('score',0):.1f}")

    # RSI signals
    for sig in rsi_buys:
        try_buy(sig["ticker"], 15.0, f"RSI oversold {sig['rsi']:.1f} | {sig['ema_trend']}")

    if not actions:
        _log(trade_log_path, "No trades triggered — all HOLD.")
        print("No trades placed this cycle.")

    print(f"\nDone. Remaining buying power: ${buying_power:.2f}")

    # Write positions snapshot for dashboard
    _write_positions(r, buying_power, actions, trade_log_path)


def _write_positions(r, buying_power: float, actions: list, trade_log_path: str):
    """Write docs/positions.json for the dashboard."""
    import os
    try:
        held = _positions(r)
        pos_list = []
        for ticker, p in held.items():
            price = _current_price(r, ticker)
            avg = p["avg_cost"]
            qty = p["quantity"]
            pnl_pct = ((price - avg) / avg * 100) if avg > 0 else 0
            pos_list.append({
                "ticker": ticker,
                "quantity": round(qty, 6),
                "avg_cost": round(avg, 4),
                "current_price": round(price, 4),
                "pnl_pct": round(pnl_pct, 2),
                "value": round(price * qty, 2),
                "stop_loss": round(avg * 0.95, 4),
                "take_profit": round(avg * 1.10, 4),
            })

        snapshot = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "buying_power": round(buying_power, 2),
            "positions": pos_list,
            "last_actions": actions[-10:],
        }

        os.makedirs("docs", exist_ok=True)
        with open("docs/positions.json", "w") as f:
            json.dump(snapshot, f, indent=2)
        print("Positions snapshot → docs/positions.json")
    except Exception as e:
        print(f"[WARN] Could not write positions.json: {e}")


if __name__ == "__main__":
    import sys
    dry = "--dry-run" in sys.argv
    execute(dry_run=dry)
