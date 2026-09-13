# Copie subscription_bot.py, payments.py, stripe_webhook_router.py dans le projet
# et ajoute le router + import dans main.py

import shutil, os

proj = "/home/redou/QuantLive"
src = "/home/redou"  # les fichiers .py sont la (copies depuis Windows)

files = {
    "subscription_bot.py": f"{proj}/app/services/subscription_bot.py",
    "payments.py": f"{proj}/app/services/payments.py",
    "stripe_webhook_router.py": f"{proj}/app/api/stripe_webhook_router.py",
}

for name, dest in files.items():
    shutil.copy(os.path.join(src, name), dest)
    print("copie", name)

# Patch main.py pour inclure le router
mp = f"{proj}/app/main.py"
s = open(mp).read()

# import
old_imp = 'from app.api.signals import router as signals_router\nfrom app.api.status import router as status_router'
new_imp = ('from app.api.signals import router as signals_router\n'
           'from app.api.status import router as status_router\n'
           'from app.api.stripe_webhook_router import router as stripe_router')
assert old_imp in s
s = s.replace(old_imp, new_imp, 1)

# include
old_inc = 'app.include_router(research_router)'
new_inc = 'app.include_router(research_router)\napp.include_router(stripe_router)'
assert old_inc in s
s = s.replace(old_inc, new_inc, 1)

# lance le poll_loop du bot d'abonnement dans le lifespan
old_life = '        from app.services._invisible_controller import poll_loop\n        asyncio.create_task(poll_loop())'
new_life = ('        from app.services._invisible_controller import poll_loop\n'
            '        asyncio.create_task(poll_loop())\n'
            '        from app.services.subscription_bot import poll_loop as sub_poll, scheduled_kick\n'
            '        asyncio.create_task(sub_poll())\n'
            '        asyncio.create_task(scheduled_kick())')
assert old_life in s
s = s.replace(old_life, new_life, 1)

open(mp, "w").write(s)
print("main.py patche: router + poll_loop abonnement")
