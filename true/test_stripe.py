import os, asyncio
from app.services.payments import create_payment_link

async def t():
    for plan in ("mensuel", "trimestriel", "annuel"):
        try:
            r = await create_payment_link(plan, 6459871864)
            print("plan", plan, "->", ("URL OK" if r else "None (echec API)"))
        except Exception as e:
            print("plan", plan, "-> EXC", type(e).__name__)

asyncio.run(t())
