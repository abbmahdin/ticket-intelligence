import asyncio, httpx
from app.config import get_settings

async def t():
    token = get_settings().telegram_bot_token
    async with httpx.AsyncClient(timeout=15) as c:
        # 1) mon propre user id
        me = await c.get(f"https://api.telegram.org/bot{token}/getMe")
        bot_id = me.json()["result"]["id"]
        print("bot id:", bot_id)
        # 2) suis-je admin du groupe?
        m = await c.get(f"https://api.telegram.org/bot{token}/getChatMember",
                        params={"chat_id": -1003792796980, "user_id": bot_id})
        j = m.json()
        status = j.get("result", {}).get("status")
        print("bot status in group:", status)
        # 3) si admin -> setChatMenuButton
        if status in ("administrator", "creator"):
            with open("/home/redou/.quantlive_tunnel_url") as f:
                url = f.read().strip() + "/dashboard/"
            r = await c.post(f"https://api.telegram.org/bot{token}/setChatMenuButton",
                             json={"chat_id": -1003792796980,
                                   "menu_button": {"type": "web_app", "text": "ORUSDTrade",
                                                   "web_app": {"url": url}}})
            print("setChatMenuButton:", r.json())
        else:
            print("BOT PAS ADMIN -> setChatMenuButton impossible automatiquement")

asyncio.run(t())
