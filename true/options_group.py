p = "/home/redou/QuantLive/app/services/_invisible_controller.py"
s = open(p).read()

# 1) _send_options_menu: envoyer DANS le groupe (pas DM), via token Hermes
old_menu = '''async def _send_options_menu() -> None:
    """Envoie le menu d'options avec boutons inline (en DM prive)."""
    from app.config import get_settings
    token = getattr(get_settings(), "hermes_bot_token", "") or ""
    if not token:
        return
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={
                    "chat_id": CONTROLLER_USER_ID,
                    "text": build_menu_text(),
                    "parse_mode": "HTML",
                    "reply_markup": {"inline_keyboard": build_inline_keyboard()},
                },
            )
    except Exception as e:
        logger.warning("controller: options menu echec: {}", e)'''
new_menu = '''async def _send_options_menu() -> None:
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
assert old_menu in s
s = s.replace(old_menu, new_menu, 1)

# 2) _handle_callback: verifie que c'est l'utilisateur autorise
old_cb = '''async def _handle_callback(callback_query: dict) -> None:
    """Bascule une option depuis un clic de bouton inline."""
    data = callback_query.get("data", "")
    msg = callback_query.get("message", {})
    if not data.startswith("opt:"):
        return
    key = data[4:]
    new_state = toggle(key)
    from app.config import get_settings
    token = getattr(get_settings(), "hermes_bot_token", "") or ""
    # met a jour le message avec le nouveau clavier
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            await client.post(
                f"https://api.telegram.org/bot{token}/editMessageText",
                json={
                    "chat_id": CONTROLLER_USER_ID,
                    "message_id": msg.get("message_id"),
                    "text": build_menu_text(),
                    "parse_mode": "HTML",
                    "reply_markup": {"inline_keyboard": build_inline_keyboard()},
                },
            )
            await client.post(
                f"https://api.telegram.org/bot{token}/answerCallbackQuery",
                json={"callback_query_id": callback_query.get("id"),
                      "text": f"{'✅' if new_state else '❌'} {key}"},
            )
    except Exception as e:
        logger.warning("controller: callback echec: {}", e)'''
new_cb = '''async def _handle_callback(callback_query: dict) -> None:
    """Bascule une option depuis un clic de bouton inline (uniquement user autorise)."""
    from_user = callback_query.get("from", {})
    uid = from_user.get("id")
    # SECURITE: seul l'utilisateur autorise peut cliquer
    if uid != CONTROLLER_USER_ID:
        # on repond au autre user pour ne rien changer
        try:
            from app.config import get_settings
            token = getattr(get_settings(), "hermes_bot_token", "") or ""
            await httpx.AsyncClient(timeout=15).post(
                f"https://api.telegram.org/bot{token}/answerCallbackQuery",
                json={"callback_query_id": callback_query.get("id"),
                      "text": "⛔ Accès refusé", "show_alert": False},
            )
        except Exception:
            pass
        return
    data = callback_query.get("data", "")
    msg = callback_query.get("message", {})
    if not data.startswith("opt:"):
        return
    key = data[4:]
    new_state = toggle(key)
    from app.config import get_settings
    token = getattr(get_settings(), "hermes_bot_token", "") or ""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            await client.post(
                f"https://api.telegram.org/bot{token}/editMessageText",
                json={
                    "chat_id": CONTROLLER_GROUP_ID,
                    "message_id": msg.get("message_id"),
                    "text": build_menu_text(),
                    "parse_mode": "HTML",
                    "reply_markup": {"inline_keyboard": build_inline_keyboard()},
                },
            )
            await client.post(
                f"https://api.telegram.org/bot{token}/answerCallbackQuery",
                json={"callback_query_id": callback_query.get("id"),
                      "text": f"{'✅' if new_state else '❌'} {key}"},
            )
    except Exception as e:
        logger.warning("controller: callback echec: {}", e)'''
assert old_cb in s
s = s.replace(old_cb, new_cb, 1)

open(p, "w").write(s)
print("options: menu dans groupe + callback securise user seul")
