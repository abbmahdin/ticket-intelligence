import asyncio, sys
sys.path.insert(0, ".")
from app.mt5_executor.config import load_settings

async def main():
    s = load_settings()
    acc = s.accounts[0]
    from metaapi_cloud_sdk import MetaApi
    api = MetaApi(s.api_key)
    # account state
    a = await api.metatrader_account_api.get_account(acc.account_id)
    print("ACCOUNT state:", getattr(a, "state", None))
    print("ACCOUNT connection_status:", getattr(a, "connection_status", None))
    print("ACCOUNT type:", getattr(a, "type", None))
    # try deploy explicitly and capture error
    try:
        await a.deploy()
        print("deploy -> OK")
    except Exception as e:
        print("deploy ERROR:", type(e).__name__, getattr(e, "details", e))
    # billing / user info
    try:
        user = await api.user_api.get_user()
        print("USER keys:", list(user.keys()) if isinstance(user, dict) else type(user))
        if isinstance(user, dict):
            for k in ("accountBalance", "balance", "currency", "enabled", "paymentMethod"):
                if k in user:
                    print("  ", k, "=", user[k])
    except Exception as e:
        print("user info ERROR:", type(e).__name__, e)

asyncio.run(main())
