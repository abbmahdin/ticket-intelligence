#!/bin/bash
SP=$(ls -d /tmp/claude-1000/*/scratchpad 2>/dev/null | head -1)
prev=0
for i in $(seq 1 900); do
  count=$(ls "$SP/transcripts/"*.txt 2>/dev/null | grep -v _dupes | wc -l)
  gpu=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader 2>/dev/null | tr -d " %")
  echo "[$(date +%H:%M:%S)] transcrites=$count/70 gpu=${gpu}%"
  if [ "$count" -ne "$prev" ]; then
    echo "  -> NOUVELLES:"; ls "$SP/transcripts/"*.txt 2>/dev/null | grep -v _dupes | xargs -n1 basename | tail -3
    prev=$count
  fi
  sleep 10
done
