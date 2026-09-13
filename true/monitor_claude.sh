#!/bin/bash
SP=$(ls -d /tmp/claude-1000/*/scratchpad 2>/dev/null | head -1)
prev=0
for i in $(seq 1 360); do
  count=$(ls "$SP"/*.txt 2>/dev/null | wc -l)
  gpu=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader 2>/dev/null | tr -d " %")
  echo "[$(date +%H:%M:%S)] txt=$count gpu=${gpu}%"
  if [ "$count" -ne "$prev" ]; then
    echo "  -> NOUVEAU txt! liste:"; ls "$SP"/*.txt 2>/dev/null | xargs -n1 basename
    prev=$count
  fi
  sleep 10
done
