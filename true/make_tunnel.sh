cat > /home/redou/.local/bin/quantlive-tunnel.sh << 'EOF'
#!/usr/bin/env bash
# Expose le dashboard QuantLive (localhost:8000) en HTTPS via cloudflared quick tunnel.
# Ecrit l'URL publique dans ~/.quantlive_tunnel_url pour le bot Telegram.
set -u
URL_FILE="$HOME/.quantlive_tunnel_url"
rm -f "$URL_FILE"
cloudflared tunnel --url http://localhost:8000 --no-autoupdate 2>&1 | while IFS= read -r line; do
    if [[ "$line" == *"trycloudflare.com"* ]]; then
        u=$(echo "$line" | grep -oE 'https://[a-zA-Z0-9.-]+\.trycloudflare\.com' | head -1)
        if [[ -n "$u" ]]; then
            echo "$u" > "$URL_FILE"
            echo "TUNNEL URL: $u"
        fi
    fi
    echo "$line"
done
EOF
chmod +x /home/redou/.local/bin/quantlive-tunnel.sh
echo "script cree"