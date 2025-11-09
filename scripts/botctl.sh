#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/wan-video-app"
RUNNER="$ROOT/scripts/run_bot.sh"
PIDFILE="/root/tg_bot.pid"
LOG="/root/tg_bot.log"

cmd_start() {
  if [[ $# -lt 1 ]]; then
    echo "Usage: $0 start <TELEGRAM_BOT_TOKEN>"
    exit 1
  fi
  local token="$1"
  chmod +x "$RUNNER"
  if [[ -f "$PIDFILE" ]] && ps -p "$(cat "$PIDFILE")" >/dev/null 2>&1; then
    echo "Bot already running (pid $(cat "$PIDFILE"))."
    exit 0
  fi
  nohup env TELEGRAM_BOT_TOKEN="$token" "$RUNNER" >/dev/null 2>&1 &
  echo $! > "$PIDFILE"
  echo "Bot started (pid $(cat "$PIDFILE")). Logs: $LOG"
}

cmd_stop() {
  if [[ -f "$PIDFILE" ]]; then
    local pid
    pid="$(cat "$PIDFILE")"
    if ps -p "$pid" >/dev/null 2>&1; then
      kill "$pid" || true
      sleep 1
      pkill -f "python -u bot/bot.py" || true
      echo "Bot stopped."
    fi
    rm -f "$PIDFILE"
  else
    pkill -f "python -u bot/bot.py" || true
    echo "No pidfile, sent stop signal if running."
  fi
}

cmd_status() {
  ps -ef | grep -v grep | grep "python -u bot/bot.py" || echo "Bot not running."
  tail -n 20 "$LOG" 2>/dev/null || echo "No log yet."
}

case "${1:-}" in
  start) shift; cmd_start "$@";;
  stop) cmd_stop;;
  restart) shift || true; cmd_stop; sleep 1; cmd_start "${1:-}";;
  status) cmd_status;;
  *) echo "Usage: $0 {start <TOKEN>|stop|restart <TOKEN>|status}"; exit 1;;
esac



