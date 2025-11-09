#!/usr/bin/env bash
set -euo pipefail

while true; do
	clear
	echo "=== WAN Watch $(date -u +"%H:%M:%S UTC") ==="
	echo
	echo "--- Processes (Wan2.2 generate.py) ---"
	pgrep -fa '/root/Wan2.2/generate.py' || echo "no generate.py running"
	echo
	echo "--- GPU ---"
	nvidia-smi --query-gpu=index,name,memory.total,memory.used,utilization.gpu --format=csv,noheader || true
	echo
	echo "--- Last output file ---"
	LAST=$(ls -1t /root/wan-video-app/outputs/*.mp4 2>/dev/null | head -n 1 || true)
	if [[ -n "${LAST:-}" ]]; then
		ls -lh "$LAST"
	else
		echo "no mp4 yet"
	fi
	echo
	echo "--- Log tail (/root/wan_wip.log) ---"
	tail -n 30 /root/wan_wip.log 2>/dev/null || echo "no log yet"
	sleep 5
done



