"""Position sizing and risk management calculations."""

from .config import (
    MAX_POSITION_SIZE, MIN_TRADE_SIZE, MAX_OPEN_POSITIONS,
    TRADEABLE_CAPITAL, STOP_LOSS_PCT, TAKE_PROFIT_PCT,
)


def position_size(available_cash: float, open_positions: int) -> float:
    """
    How many dollars to deploy in a single new position.
    Scales down as positions fill up to avoid over-concentration.
    """
    if open_positions >= MAX_OPEN_POSITIONS:
        return 0.0
    slots_left = MAX_OPEN_POSITIONS - open_positions
    # Equal-weight the remaining capital across remaining slots
    per_slot = min(available_cash / slots_left, MAX_POSITION_SIZE)
    if per_slot < MIN_TRADE_SIZE:
        return 0.0
    return round(per_slot, 2)


def stop_loss_price(entry_price: float) -> float:
    return round(entry_price * (1 - STOP_LOSS_PCT), 4)


def take_profit_price(entry_price: float) -> float:
    return round(entry_price * (1 + TAKE_PROFIT_PCT), 4)


def check_exit(entry_price: float, current_price: float) -> str:
    """Return 'STOP_LOSS', 'TAKE_PROFIT', or 'HOLD'."""
    if current_price <= stop_loss_price(entry_price):
        return "STOP_LOSS"
    if current_price >= take_profit_price(entry_price):
        return "TAKE_PROFIT"
    return "HOLD"


def risk_summary(entry_price: float, dollar_amount: float) -> dict:
    shares = dollar_amount / entry_price
    sl = stop_loss_price(entry_price)
    tp = take_profit_price(entry_price)
    max_loss = (entry_price - sl) * shares
    max_gain = (tp - entry_price) * shares
    return {
        "entry": entry_price,
        "stop_loss": sl,
        "take_profit": tp,
        "shares": round(shares, 6),
        "max_loss_usd": round(max_loss, 2),
        "max_gain_usd": round(max_gain, 2),
        "risk_reward": round(max_gain / max_loss, 2) if max_loss > 0 else 0,
    }
