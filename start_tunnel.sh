#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$BASE_DIR"

URLFILE="logs/tunnel_url.txt"
CLOUDFLARED_BIN="${CLOUDFLARED_BIN:-cloudflared}"

mkdir -p logs
rm -f "$URLFILE"

"$CLOUDFLARED_BIN" tunnel --url http://localhost:5001 2>&1 | \
while IFS= read -r line; do
    echo "$line"
    if [[ "$line" =~ https://[a-z0-9-]+\.trycloudflare\.com ]]; then
        echo "${BASH_REMATCH[0]}" > "$URLFILE"
    fi
done
