import json, urllib.request, os, sys

KEY = open(os.path.expanduser("~/.quantlive-secrets-backup/.n8n_api_key_found")).read().strip()
H = {"X-N8N-API-KEY": KEY, "Content-Type": "application/json"}
BASE = "http://localhost:5678/api/v1"
PG_CRED = {"id": "4KgZYrQB15K4fpbr", "name": "QuantLive Postgres"}
TG_CRED = {"id": "a1cf4abee1304724", "name": "Telegram Bot"}


def api(method, path, body=None, timeout=25):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=H)
    try:
        return json.load(urllib.request.urlopen(req, timeout=timeout))
    except urllib.error.HTTPError as e:
        return {"__error__": e.code, "__body__": e.read().decode()[:300]}


SQL_DRIFT = """
SELECT
  st.name            AS strategy_name,
  s.strategy_id      AS strategy_id,
  ROUND(100.0 * s.wins / s.n, 1)                    AS real_wr_pct,
  ROUND(100.0 * bt.win_rate, 1)                     AS backtest_wr_pct,
  ROUND(100.0 * s.wins / s.n - 100.0 * bt.win_rate, 1) AS drift_pp,
  s.n                AS real_trades,
  bt.total_trades    AS backtest_trades
FROM (
  SELECT s.strategy_id,
         COUNT(*) FILTER (WHERE o.result IN ('tp1_hit','tp2_hit','tp1_then_expired')) AS wins,
         COUNT(*) FILTER (WHERE o.result IN ('tp1_hit','tp2_hit','tp1_then_expired','sl_hit')) AS n
  FROM outcomes o JOIN signals s ON s.id = o.signal_id
  WHERE s.created_at >= NOW() - interval '90 days'
    AND o.result IN ('tp1_hit','tp2_hit','tp1_then_expired','sl_hit')
  GROUP BY s.strategy_id
  HAVING COUNT(*) >= 5
) s
JOIN (
  SELECT DISTINCT ON (strategy_id) strategy_id, win_rate, total_trades
  FROM backtest_results
  WHERE is_walk_forward IS NOT TRUE AND win_rate IS NOT NULL
  ORDER BY strategy_id, created_at DESC
) bt ON bt.strategy_id = s.strategy_id
LEFT JOIN strategies st ON st.id = s.strategy_id
WHERE 100.0 * s.wins / s.n < 100.0 * bt.win_rate - 20
ORDER BY drift_pp ASC;
"""

CODE_FORMAT = r"""
const rows = $input.all().map(i => i.json);
const seuil = Number($env.DRIFT_ALERT_THRESHOLD_PP || 20);
const lines = rows.map(d => {
  return [
    '⚠️ *Régime de marché cassé — Drift Alert*',
    '',
    '• Stratégie : *' + (d.strategy_name || ('id ' + d.strategy_id)) + '*',
    '• Winrate réel (90j) : *' + d.real_wr_pct + '%* (' + d.real_trades + ' trades)',
    '• Winrate backtest : ' + d.backtest_wr_pct + '% (' + d.backtest_trades + ' trades)',
    '• Dérive : *' + d.drift_pp + ' pp* (seuil -' + seuil + ' pp)',
    '',
    '⚡ Réduis les lots ou arrête le bot.',
    '_Vérifié le ' + new Date().toLocaleString('fr-FR', { timeZone: 'Europe/Brussels' }) + '_'
  ].join('\n');
});
return rows.map((d, i) => ({ json: Object.assign({}, d, { message: lines[i] }) }));
"""

NODES = [
    {
        "parameters": {"rule": {"interval": [{"field": "cronExpression", "expression": "0 */6 * * *"}]}},
        "id": "drift_cron",
        "name": "Cron Drift (6h)",
        "type": "n8n-nodes-base.scheduleTrigger",
        "typeVersion": 1.2,
        "position": [0, 300],
    },
    {
        "parameters": {"operation": "executeQuery", "query": SQL_DRIFT, "options": {}},
        "id": "drift_sql",
        "name": "Drift SQL",
        "type": "n8n-nodes-base.postgres",
        "typeVersion": 2,
        "position": [220, 300],
        "credentials": {"postgres": PG_CRED},
    },
    {
        "parameters": {"jsCode": CODE_FORMAT},
        "id": "drift_format",
        "name": "Formatter Alerte",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [440, 300],
    },
    {
        "parameters": {
            "resource": "message",
            "operation": "sendMessage",
            # [OPS DM 2026-08-22] Alerte drift = ops -> DM admin, jamais le groupe
            # des abonnes (miroir du workflow HR1tZTFQRIEPKbrB deja en base).
            "chatId": "={{ $env.TELEGRAM_DM_CHAT_ID }}",
            "text": "={{ $json.message }}",
            "additionalFields": {"parse_mode": "Markdown"},
        },
        "id": "drift_tg",
        "name": "Telegram Alerte",
        "type": "n8n-nodes-base.telegram",
        "typeVersion": 2.1,
        "position": [660, 300],
        "credentials": {"telegramApi": TG_CRED},
    },
]

CONNECTIONS = {
    "Cron Drift (6h)": {"main": [[{"node": "Drift SQL", "type": "main", "index": 0}]]},
    "Drift SQL": {"main": [[{"node": "Formatter Alerte", "type": "main", "index": 0}]]},
    "Formatter Alerte": {"main": [[{"node": "Telegram Alerte", "type": "main", "index": 0}]]},
}

BODY = {
    "name": "QuantLive - Live vs Backtest Drift Alert",
    "nodes": NODES,
    "connections": CONNECTIONS,
    "settings": {"executionOrder": "v1", "timezone": "Europe/Brussels"},
}

res = api("POST", "/workflows", BODY)
if "__error__" in res:
    print("ECHEC creation:", res["__error__"], res.get("__body__", ""))
    sys.exit(1)
wid = res["id"]
print("Workflow cree:", wid, "-", res.get("name"))

act = api("POST", f"/workflows/{wid}/activate")
if "__error__" in act:
    print("ECHEC activation:", act["__error__"], act.get("__body__", ""))
    sys.exit(1)
print("Active:", act.get("active"))

# Verification
full = api("GET", f"/workflows/{wid}")
print("\n=== Nodes ===")
for n in full.get("nodes", []):
    print(f"  - {n.get('name')} [{n.get('type')}]")
print("workflow id:", wid)
