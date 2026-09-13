#!/bin/bash
while true; do
  done=$(ls /tmp/transcripts_V/*.txt 2>/dev/null | wc -l)
  pct=$((done*100/70))
  claude=$(tmux capture-pane -t claude-clean -p -S -2 2>/dev/null | grep -oE "❯ [0-9]+" | tail -1)
  gpu=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader 2>/dev/null | tr -d " %")
  echo "[$(date +%H:%M:%S)] TRANSCRIT=$done/70 (${pct}%) | GPU=${gpu}% | Claude:${claude}"
  sleep 10
done
