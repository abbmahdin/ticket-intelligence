#!/usr/bin/env bash
# Lance l'agent de code Kimi K3 (OpenRouter)
cd /home/redou/QuantLive
export NVM_DIR="$HOME/.nvm"; [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" >/dev/null 2>&1
export PATH="$HOME/.local/bin:$PATH"
exec .venv/bin/python /home/redou/QuantLive/kimi_coder.py "$@"
