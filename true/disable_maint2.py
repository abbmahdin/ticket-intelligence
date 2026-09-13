p = "/home/redou/QuantLive/app/main.py"
s = open(p).read()

# 1) startup: neutralise l'appel
old1 = '''        logger.exception("Controleur invisible impossible a demarrer")
    await _notify_maintenance(
        "✅ ORUSDTrade redémarré — Service opérationnel.\\n"
        "📡 Les signaux XAU/USD reprennent automatiquement."
    )'''
new1 = '''        logger.exception("Controleur invisible impossible a demarrer")
    # [V 2026-07-17] Maintenance notifications DESACTIVEES (demande utilisateur)
    # await _notify_maintenance(
    #     "✅ ORUSDTrade redémarré — Service opérationnel.\\n"
    #     "📡 Les signaux XAU/USD reprennent automatiquement."
    # )'''
assert old1 in s, "old1 introuvable"
s = s.replace(old1, new1, 1)

# 2) shutdown: deja commente, OK
open(p, "w").write(s)
print("startup maintenance commente")
