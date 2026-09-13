import asyncio, sys, json
sys.path.insert(0, ".")
from app.mt5_executor.config import load_settings

async def main():
    s = load_settings()
    if not s.api_key:
        print("MT5_API_KEY absente"); return
    for acc in s.accounts:
        if not acc.enabled:
            continue
        if acc.account_id:
            print("account_id deja present pour %s: %s" % (acc.name, acc.account_id))
            continue
        from metaapi_cloud_sdk import MetaApi
        api = MetaApi(s.api_key)
        try:
            created = await api.metatrader_account_api.create_account({
                "name": acc.name,
                "type": "cloud",
                "login": acc.login,
                "password": acc.password,
                "server": acc.server,
                "platform": "mt5",
                "magic": s.magic,
                "application": "QuantLive",
                "demonstration": bool(acc.demo),
            })
            aid = created.id if hasattr(created, "id") else created.get("id")
            print("COMPTE CREE %s -> account_id=%s" % (acc.name, aid))
            # sauvegarde dans mt5_accounts.json
            path = "mt5_accounts.json"
            raw = json.loads(open(path, encoding="utf-8").read())
            for a in raw["accounts"]:
                if a["name"] == acc.name:
                    a["account_id"] = aid
            json.dump(raw, open(path, "w", encoding="utf-8"), indent=2)
            print("mt5_accounts.json mis a jour avec account_id")
        except Exception as e:
            print("ECHEC creation %s: %s: %s" % (acc.name, type(e).__name__, e))

asyncio.run(main())
