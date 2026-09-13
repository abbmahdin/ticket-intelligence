p = "/home/redou/QuantLive/app/main.py"
s = open(p).read()

# 1) neutralise les 2 appels (startup + shutdown)
s = s.replace(
    '''    logger.info("GoldSignal application started")

    # [V 2026-07-17] Controleur invisible ORUSDTrade (commandes Hermes, resultat en DM)
    try:
        from app.services._invisible_controller import poll_loop
        asyncio.create_task(poll_loop())
        logger.info("Controleur invisible ORUSDTrade demarre")
    except Exception:
        logger.exception("Controleur invisible impossible a demarrer")

    # [V 2026-07-17] Alerte maintenance/redemarrage (desactivee sur demande utilisateur)
    await _notify_maintenance(
        "✅ ORUSDTrade redémarré — Service opérationnel.\\n"
        "📡 Les signaux XAU/USD reprennent automatiquement."
    )''',
    '''    logger.info("GoldSignal application started")

    # [V 2026-07-17] Controleur invisible ORUSDTrade (commandes Hermes, resultat en DM)
    try:
        from app.services._invisible_controller import poll_loop
        asyncio.create_task(poll_loop())
        logger.info("Controleur invisible ORUSDTrade demarre")
    except Exception:
        logger.exception("Controleur invisible impossible a demarrer")

    # [V 2026-07-17] Maintenance notifications DESACTIVEES (demande utilisateur)''',
)

s = s.replace(
    '''    # Graceful shutdown
    await _notify_maintenance(
        "🔧 ORUSDTrade en maintenance — Redémarrage en cours.\\n"
        "⏳ Les signaux reprendront dès le service rétabli."
    )
    if scheduler.running:''',
    '''    # Graceful shutdown
    # [V 2026-07-17] Maintenance notifications DESACTIVEES (demande utilisateur)
    if scheduler.running:''',
)

open(p, "w").write(s)
print("maintenance desactivee dans main.py")
