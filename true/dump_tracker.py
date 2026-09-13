import json, urllib.request, os, asyncio, sys

KEY = open(os.path.expanduser("~/.quantlive-secrets-backup/.n8n_api_key_found")).read().strip()
H = {"X-N8N-API-KEY": KEY}
BASE = "http://localhost:5678/api/v1"

req = urllib.request.Request(f"{BASE}/workflows/0f42de21-4419-4c2d-825a-6a720a37c94c", headers=H)
full = json.load(urllib.request.urlopen(req, timeout=15))

print("=== NODES COMPLETS DU TRACKER ===")
for n in full.get("nodes", []):
    print(f"\n--- [{n.get('name')}] type={n.get('type')}")
    print(json.dumps(n.get("parameters", {}), ensure_ascii=False)[:1500])

print("\n=== CONNECTIONS ===")
print(json.dumps(full.get("connections", {}), ensure_ascii=False))

# Outcomes: valeurs distinctes de result + winrate reel par strategie
sys.path.insert(0, "/home/redou/QuantLive")
from dotenv import load_dotenv
load_dotenv("/home/redou/QuantLive/.env")
from app.database import async_session_factory
from sqlalchemy import text

async def main():
    async with async_session_factory() as s:
        r = await s.execute(text("SELECT result, COUNT(*) FROM outcomes GROUP BY result ORDER BY 2 DESC"))
        print("\n=== outcomes.result distincts ===")
        for row in r:
            print("  ", row[0], "=", row[1])
        r = await s.execute(text("""
            SELECT s.strategy_id, COUNT(o.id) AS n,
                   COUNT(*) FILTER (WHERE o.result IN ('tp1_hit','tp2_hit','tp_hit','profit','tp1','tp2')) AS wins
            FROM outcomes o JOIN signals s ON s.id = o.signal_id
            GROUP BY s.strategy_id ORDER BY n DESC LIMIT 8
        """))
        print("\n=== trades reels par strategie ===")
        for row in r:
            print("  strategy", row[0], ":", row[1], "trades,", row[2], "wins")
        r = await s.execute(text("""
            SELECT DISTINCT o.result FROM outcomes o
            JOIN signals s ON s.id = o.signal_id
            WHERE s.strategy_id IS NOT NULL
        """))
        print("\n=== resultats par strategie ===")
        for row in r:
            print("  ", row[0])

asyncio.run(main())
