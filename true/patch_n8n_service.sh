#!/bin/bash
set -euo pipefail

SVC=~/.config/systemd/user/n8n.service
ENV=/home/redou/QuantLive/.env
TS=$(date +%Y%m%d_%H%M%S)

echo "=== Backup ==="
cp "$SVC" "${SVC}.bak_addenv_${TS}"
echo "backup: ${SVC}.bak_addenv_${TS}"

# Lire les cles depuis le .env QuantLive (si presentes)
get_env() {
  grep -E "^$1=" "$ENV" | head -1 | cut -d= -f2- | tr -d '\r"'
}

TWELVE=$(get_env TWELVE_DATA_API_KEY)
TBOT=$(get_env TELEGRAM_BOT_TOKEN)

add_env() {
  local key="$1" val="$2"
  if [ -z "$val" ]; then
    echo "  (skip $key : absente du .env)"
    return
  fi
  if grep -qE "^Environment=${key}=" "$SVC"; then
    echo "  (deja presente : $key)"
    return
  fi
  # inserer avant la derniere ligne Environment= (MT4_BRIDGE_URL)
  sed -i "/^Environment=MT4_BRIDGE_URL=/i Environment=${key}=${val}" "$SVC"
  echo "  ajoutee : Environment=${key}=<set>"
}

echo "=== Ajout des cles manquantes ==="
add_env TWELVE_DATA_API_KEY "$TWELVE"
add_env TELEGRAM_BOT_TOKEN "$TBOT"

echo "=== Verification des lignes Environment ==="
grep -n "^Environment=" "$SVC" | sed -E 's/=(.{0,5}).*/=<set>/'

echo "=== daemon-reload + restart n8n ==="
systemctl --user daemon-reload
systemctl --user restart n8n.service
sleep 12

echo "=== Etat du service ==="
systemctl --user is-active n8n.service
systemctl --user show n8n.service -p ActiveEnterTimestamp --no-pager 2>/dev/null
