# Linux setup

## 1. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2. Configure Robinhood credentials

Use either a token bundle:

```bash
export RH_TOKEN="..."
```

or username/password with TOTP:

```bash
export RH_USERNAME="you@example.com"
export RH_PASSWORD="..."
export RH_TOTP_SECRET="..."
```

## 3. Run a dry run first

```bash
chmod +x run_trade.sh start_tunnel.sh auto_trade.sh
./run_trade.sh --dry-run
```

## 4. Run live only after validating dry-run output

```bash
./run_trade.sh
```

## 5. Optional scheduled run with cron

```cron
0 10-15 * * 1-5 cd /path/to/robinhood-trading-bot && ./run_trade.sh >> logs/cron.log 2>&1
```

The app now uses `run_trade.sh`, which runs the deterministic Python executor instead of asking Claude to place trades from a prompt.
