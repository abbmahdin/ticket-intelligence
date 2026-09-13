import os, asyncio
from dotenv import load_dotenv
load_dotenv("/home/redou/QuantLive/.env")
from app.config import get_settings
s = get_settings()
print("via get_settings STRIPE_SECRET_KEY present:", bool(s.stripe_secret_key))
print("via os.environ present:", bool(os.environ.get("STRIPE_SECRET_KEY")))
from app.services.payments import create_payment_link
async def t():
    r = await create_payment_link("mensuel", 6459871864)
    print("apres load_dotenv create_payment_link ->", ("URL OK" if r else "None"))
asyncio.run(t())
