# Robinhood Trading Bot - How It Works

## What This Project Does

This project generates trading signals for a small Robinhood trading account using two indicator-based strategies:

- RSI + VWAP + EMA momentum signals
- A 3-day net-buy trend signal

The Python strategy code is the core of the bot and is the part that is intended to run on both Windows and Linux.

## Platform Notes

### Works on both Windows and Linux

- Installing Python dependencies
- Running the strategy manually
- Reading logs and signal output
- Editing configuration in `strategy/config.py`

### Linux support

Linux is the best fit for unattended or always-on use.

- You can run the strategy manually from a shell
- You can automate recurring runs with `cron` or `systemd`
- The included `.sh` scripts are Unix-style and are meant for Linux or other Unix-like environments

### Windows support

Windows supports the Python strategy, but the included automation scripts are not native Windows scripts.

- Run the strategy with Python from PowerShell or Command Prompt
- Use Task Scheduler if you want scheduled runs on Windows
- If you want to use the included `.sh` scripts, run them through Git Bash or WSL

## Common Commands

### Run once manually

Windows:

```powershell
python -m strategy.run
```

Linux:

```bash
python3 -m strategy.run
```

### View latest signals

Windows:

```powershell
Get-Content logs/latest_signals.json
```

Linux:

```bash
cat logs/latest_signals.json
```

### View trade history

Windows:

```powershell
Get-Content logs/trade_log.md
```

Linux:

```bash
cat logs/trade_log.md
```

### Follow the automation log

Windows:

```powershell
Get-Content logs/auto_run.log -Wait
```

Linux:

```bash
tail -f logs/auto_run.log
```

## How the Strategy Decides

Two strategies run side by side. If both agree, that is treated as a stronger signal than either one alone.

### Watchlist

`SPY`, `QQQ`, `AAPL`, `MSFT`, `NVDA`

### Strategy 1: RSI + VWAP + EMA

Buy when at least 2 of these are true:

1. RSI is below the oversold threshold
2. Price is below VWAP
3. A bullish EMA crossover appears

Sell when at least 2 of these are true:

1. RSI is above the overbought threshold
2. Price is above VWAP
3. A bearish EMA crossover appears

### Strategy 2: 3-Day Net Buy Trend

This looks for buying pressure that strengthens across multiple days.

Buy when all of these are true:

1. Net buy increases across three consecutive days
2. The trend has lasted at least three days
3. OBV slope is rising

Sell when both of these are true:

1. Net buy reverses
2. OBV slope is falling

## Risk Limits

Current repo defaults are intended to stay small and controlled:

- Small account size
- Cash buffer left unspent
- Capped position sizes
- Limited number of open positions
- Stop-loss and take-profit exits

Check `strategy/config.py` for the exact values currently active in this branch.

## Automation Notes

This repo includes shell scripts such as `trade.sh`, `setup.sh`, `install.sh`, and `auto_trade.sh`.

- Those scripts are Bash-oriented
- Some of them still contain older machine-specific paths or Mac-specific assumptions
- Treat them as templates unless you have already customized them for your own machine

For Linux, the usual next step is adapting the automation to `cron` or `systemd`.

For Windows, the usual next step is creating a Task Scheduler job that runs the Python command on the schedule you want.

## File Guide

```text
robinhood-trading-bot/
|-- HOW_IT_WORKS.md
|-- README.md
|-- SETUP.md
|-- requirements.txt
|-- trade.sh
|-- auto_trade.sh
|-- strategy/
|   |-- config.py
|   |-- indicators.py
|   |-- market_data.py
|   |-- net_buy.py
|   |-- risk.py
|   |-- run.py
|   `-- signals.py
`-- logs/
    |-- latest_signals.json
    |-- trade_log.md
    `-- auto_run.log
```

## If Something Looks Wrong

1. Run the strategy manually and read the console output
2. Check `logs/latest_signals.json`
3. Check `logs/auto_run.log`
4. Review the thresholds and sizing rules in `strategy/config.py`

## Git Note

This file was updated to clarify the current Windows and Linux workflow:

- Python strategy usage is cross-platform
- Included automation scripts are Unix/Bash-first
- Windows automation should use Task Scheduler or a Bash-compatible environment
- Linux automation should use normal scheduler tooling such as `cron` or `systemd`
