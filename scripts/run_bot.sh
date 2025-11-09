#!/usr/bin/env bash
set -euo pipefail

TOKEN="${TELEGRAM_BOT_TOKEN:-}"
if [[ -z "$TOKEN" ]]; then
  echo "TELEGRAM_BOT_TOKEN not set"
  exit 1
fi

ROOT="/root/wan-video-app"
LOG="/root/tg_bot.log"
VENV="$ROOT/.venv"

cd "$ROOT"
. "$VENV/bin/activate"

echo "Starting bot loop at $(date -u '+%F %T UTC')" | tee -a "$LOG"
ATTEMPT=0
while true; do
  ATTEMPT=$((ATTEMPT+1))
  echo "[${ATTEMPT}] Launching bot at $(date -u '+%T UTC')" | tee -a "$LOG"
  TELEGRAM_BOT_TOKEN="$TOKEN" python -u bot/bot.py >> "$LOG" 2>&1 || true
  echo "[${ATTEMPT}] Bot exited with code $? at $(date -u '+%T UTC'), restarting in 5s..." | tee -a "$LOG"
  sleep 5
done



