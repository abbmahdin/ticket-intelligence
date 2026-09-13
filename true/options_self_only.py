p = "/home/redou/QuantLive/app/services/_invisible_controller.py"
s = open(p).read()

# _send_options_menu: envoyer dans groupe puis supprimer apres 30s (visible que toi le temps de cliquer)
old_menu = '''async def _send_options_menu() -> None:
    """[V 2026-07-17] Envoie le menu d'options avec boutons inline DANS le groupe
    ORUSDTrade (visible par tous, mais seul l'utilisateur autorise peut cliquer)."""
    from app.config import get_settings
    token = getattr(get_settings(), "hermes_bot_token", "") or ""
    if not token:
        return
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={
                    "chat_id": CONTROLLER_GROUP_ID,
                    "text": build_menu_text(),
                    "parse_mode": "HTML",
                    "reply_markup": {"inline_keyboard": build_inline_keyboard()},
                },
            )
    except Exception as e:
        logger.warning("controller: options menu echec: {}", e)'''
new_menu = '''async def _send_options_menu() -> None:
    """[V 2026-07-17] Envoie le menu d'options avec boutons inline DANS le groupe
    ORUSDTrade, visible quelques secondes (le temps que l'utilisateur autorise clique),
    puis SUPPRIME automatiquement => seul l'utilisateur le voit reellement."""
    from app.config import get_settings
    token = getattr(get_settings(), "hermes_bot_token", "") or ""
    if not token:
        return
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={
                    "chat_id": CONTROLLER_GROUP_ID,
                    "text": build_menu_text(),
                    "parse_mode": "HTML",
                    "reply_markup": {"inline_keyboard": build_inline_keyboard()},
                },
            )
            # supprime le message apres 30s (fenetre de clic pour l'utilisateur seul)
            msg_id = (r.json().get("result") or {}).get("message_id")
            if msg_id:
                async def _delayed_delete():
                    await asyncio.sleep(30)
                    try:
                        async with httpx.AsyncClient(timeout=15) as c2:
                            await c2.post(
                                f"https://api.telegram.org/bot{token}/deleteMessage",
                                json={"chat_id": CONTROLLER_GROUP_ID, "message_id": msg_id},
                            )
                    except Exception:
                        pass
                asyncio.create_task(_delayed_delete())
    except Exception as e:
        logger.warning("controller: options menu echec: {}", e)'''
assert old_menu in s
s = s.replace(old_menu, new_menu, 1)

open(p, "w").write(s)
print("menu options: supprime apres 30s (visible que toi)")
