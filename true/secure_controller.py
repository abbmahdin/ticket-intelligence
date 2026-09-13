p = "/home/redou/QuantLive/app/services/_invisible_controller.py"
s = open(p).read()

# 1) _force_recap : plus de post groupe, confirmation DM seulement
o1 = '''async def _force_recap() -> str:
    try:
        from app.workers.extra_jobs import send_economic_calendar_recap
        await send_economic_calendar_recap()
        return "✅ Récap économique envoyé dans ORUSDTrade"
    except Exception as e:
        return f"❌ recap erreur: {e}"'''
n1 = '''async def _force_recap() -> str:
    # [V 2026-07-17] Aucun echo dans le groupe: on declenche le job (qui poste deja
    # dans ORUSDTrade via le bot) mais la confirmation revient en DM prive.
    try:
        from app.workers.extra_jobs import send_economic_calendar_recap
        await send_economic_calendar_recap()
        return "✅ Récap économique déclenché (posté dans ORUSDTrade par le bot)"
    except Exception as e:
        return f"❌ recap erreur: {e}"'''
assert o1 in s
s = s.replace(o1, n1, 1)

# 2) _force_bias
o2 = '''async def _force_bias() -> str:
    try:
        from app.workers.extra_jobs import send_morning_mtf_bias
        await send_morning_mtf_bias()
        return "✅ Bias MTF envoyé dans ORUSDTrade"
    except Exception as e:
        return f"❌ bias erreur: {e}"'''
n2 = '''async def _force_bias() -> str:
    try:
        from app.workers.extra_jobs import send_morning_mtf_bias
        await send_morning_mtf_bias()
        return "✅ Bias MTF déclenché (posté dans ORUSDTrade par le bot)"
    except Exception as e:
        return f"❌ bias erreur: {e}"'''
assert o2 in s
s = s.replace(o2, n2, 1)

# 3) _maintenance_msg : supprime le post groupe (deja desactive au demarrage, mais
#    on securise: plus de _send_message dans le groupe)
o3 = '''async def _maintenance_msg() -> str:
    try:
        notifier = _make_notifier()
        await notifier._send_message(
            "🔧 ORUSDTrade en maintenance — Redémarrage en cours.\\n⏳ Les signaux reprendront dès le service rétabli."
        )
        return "✅ Message maintenance envoyé"
    except Exception as e:'''
n3 = '''async def _maintenance_msg() -> str:
    # [V 2026-07-17] SECURITE: aucun message de maintenance dans le groupe.
    # On ne fait QUE confirmer en DM prive (voir handle_command -> _dm).
    return "ℹ️ Commande maintenance reçue (aucun message public dans le groupe)"'''
assert o3 in s
s = s.replace(o3, n3, 1)

# Retire le bloc except restant de l'ancien _maintenance_msg (le 'except Exception as e:')
# qui reference notifier. On le remplace par rien.
o4 = '''        return "ℹ️ Commande maintenance reçue (aucun message public dans le groupe)"
    except Exception as e:
        return f"❌ maintenance erreur: {e}"'''
n4 = '''        return "ℹ️ Commande maintenance reçue (aucun message public dans le groupe)"'''
assert o4 in s
s = s.replace(o4, n4, 1)

open(p, "w").write(s)
print("controller: aucun echo dans le groupe")
