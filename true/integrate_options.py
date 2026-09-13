p = "/home/redou/QuantLive/app/services/_invisible_controller.py"
s = open(p).read()

# 1) import du menu d'options
old_imp = '''from app.config import get_settings
from app.database import async_session_factory
from app.models.outcome import Outcome
from app.models.signal import Signal
from app.services.telegram_notifier import TelegramNotifier'''
new_imp = '''from app.config import get_settings
from app.database import async_session_factory
from app.models.outcome import Outcome
from app.models.signal import Signal
from app.services.telegram_notifier import TelegramNotifier
from app.services._options_menu import (
    build_menu_text,
    build_inline_keyboard,
    toggle,
    is_on,
)'''
assert old_imp in s
s = s.replace(old_imp, new_imp, 1)

# 2) ajoute /options dans handle_command (apres help)
old_help_ret = '''        await _dm(
            "🎛 COMMANDES ORUSDTrade (invisibles)\\n"
            "/stats — win-rate 24h + actifs\\n"
            "/status — état services\\n"
            "/pause — coupe le scanner\\n"
            "/resume — relance le scanner\\n"
            "/recap — force récap économique\\n"
            "/bias — force bias MTF\\n"
            "/maintenance — message maintenance\\n"
            "/help — cette aide"
        )
        return True'''
new_help_ret = '''        await _dm(
            "🎛 COMMANDES ORUSDTrade (invisibles)\\n"
            "/stats — win-rate 24h + actifs\\n"
            "/status — état services\\n"
            "/pause — coupe le scanner\\n"
            "/resume — relance le scanner\\n"
            "/recap — force récap économique\\n"
            "/bias — force bias MTF\\n"
            "/maintenance — message maintenance\\n"
            "/options — menu features (boutons)\\n"
            "/help — cette aide"
        )
        return True
    if cmd == "options":
        await _send_options_menu()
        return True'''
assert old_help_ret in s
s = s.replace(old_help_ret, new_help_ret, 1)

# 3) ajoute _send_options_menu + _handle_callback avant _dm
old_dm_def = '''async def _dm(text: str) -> None:'''
new_dm_def = '''async def _send_options_menu() -> None:
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
        logger.warning("controller: options menu echec: {}", e)


async def _handle_callback(callback_query: dict) -> None:
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
        logger.warning("controller: callback echec: {}", e)


async def _dm(text: str) -> None:'''
assert old_dm_def in s
s = s.replace(old_dm_def, new_dm_def, 1)

# 4) poll_loop: traite aussi callback_query
old_poll = '''                    text = msg.get("text", "")
                    mid = msg.get("message_id")
                    if text:
                        # Supprime le message de commande dans le groupe (invisible)
                        if cid == CONTROLLER_GROUP_ID and uid == CONTROLLER_USER_ID:
                            await _delete_msg(mid)
                        await handle_command(text, uid, cid, mid)'''
new_poll = '''                    text = msg.get("text", "")
                    mid = msg.get("message_id")
                    if text:
                        # Supprime le message de commande dans le groupe (invisible)
                        if cid == CONTROLLER_GROUP_ID and uid == CONTROLLER_USER_ID:
                            await _delete_msg(mid)
                        await handle_command(text, uid, cid, mid)
                    # callback_query (boutons inline du menu options)
                    cb = upd.get("callback_query")
                    if cb:
                        await _handle_callback(cb)'''
assert old_poll in s
s = s.replace(old_poll, new_poll, 1)

open(p, "w").write(s)
print("menu options + callbacks integres")
