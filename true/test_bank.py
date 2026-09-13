import asyncio, sys, os
sys.path.insert(0, "/home/redou/QuantLive")
from dotenv import load_dotenv; load_dotenv("/home/redou/QuantLive/.env")
import app.services.subscription_logic as L
cap = []
async def fake_tg(token, method, **kw):
    if method == "sendMessage":
        cap.append(kw)
L._tg = fake_tg
async def t():
    await L.cmd_pay_public(-1003792796980, 999999, "/pay mensuel")
    for i, m in enumerate(cap):
        print(f"--- message {i+1} ---")
        print(m.get("text", "")[:400])
asyncio.run(t())
