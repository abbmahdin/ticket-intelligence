"""Bot d'abonnement maison pour ORUSDTrade (groupe payant XAUUSD).

Architecture autonome, token SEPARE du bot agent Hermes (evite le conflit de
long-polling qu'on a eu sur /mini). Utilise httpx + polling maison (comme
_invisible_controller).

Fonctionnalites:
- /pay           -> genere une adresse USDT (ERC20/TRC20) + montant + QR (image)
- /status        -> affiche l'etat de l'abonnement de l'utilisateur
- /renew         -> relance un paiement
- ADMIN (/approve, /deny, /list, /kick) -> gestion manuelle (validation paiement)
- Stockage SQLite local: ~/.quantlive_subs.db
- Tache planifiee: kick les abonnements expires du groupe ORUSDTrade

SECURITE: seul l'admin (ADMIN_USER_ID) peut approver/refuser. Les paiements
crypto sont valides MANUELLEMENT par l'admin (pas d'API tierce) => pas de KYC.

Lancement:
- Via QuantLive: app/services/subscription_bot.py, importe depuis app.main
  (poll_loop + scheduled_kick demarres dans le lifespan).
- Standalone: ``python subscription_bot.py`` (lecture .env via os.environ).
"""

import asyncio
import os
import sqlite3
import sys
import time
from datetime import datetime, timedelta, timezone

import httpx
from loguru import logger

# --- Config (via app.config.get_settings si dispo, sinon os.environ) ---
# Le bot vit dans QuantLive/app/services/ et est importe par app.main (cwd
# QuantLive, `app.*` resolvable). Il peut aussi etre lance en standalone
# depuis /home/redou : on injecte alors le chemin QuantLive pour pouvoir
# importer app.config. Sans QuantLive, on retombe sur les variables d'env.
_QUANTLIVE_DIR = os.path.expanduser(
    os.environ.get("QUANTLIVE_DIR", "/home/redou/QuantLive")
)
if os.path.isdir(_QUANTLIVE_DIR) and _QUANTLIVE_DIR not in sys.path:
    sys.path.insert(0, _QUANTLIVE_DIR)

try:
    from app.config import get_settings
    _S = get_settings()
    SUB_BOT_TOKEN = getattr(_S, "subscription_bot_token", "") or os.environ.get("SUBSCRIPTION_BOT_TOKEN", "")
    GROUP_CHAT_ID = int(getattr(_S, "telegram_chat_id", "") or os.environ.get("TELEGRAM_CHAT_ID", "-1003792796980"))
    SIGNALS_TOKEN = getattr(_S, "telegram_bot_token", "") or os.environ.get("TELEGRAM_BOT_TOKEN", "")
except Exception:
    SUB_BOT_TOKEN = os.environ.get("SUBSCRIPTION_BOT_TOKEN", "")
    GROUP_CHAT_ID = int(os.environ.get("TELEGRAM_CHAT_ID", "-1003792796980"))
    SIGNALS_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

ADMIN_USER_ID = int(os.environ.get("SUBSCRIPTION_ADMIN_ID", "6459871864"))

# Adresse USDT (a remplir dans .env: SUBSCRIPTION_USDT_ADDRESS)
USDT_ADDRESS = os.environ.get("SUBSCRIPTION_USDT_ADDRESS", "<A_REMPLIR_DANS_ENV>")
USDT_NETWORK = os.environ.get("SUBSCRIPTION_USDT_NETWORK", "TRC20")

# Plans: nom -> (jours, prix USDT)
PLANS = {
    "mensuel": (30, 50),
    "trimestriel": (90, 130),
    "annuel": (365, 450),
}

DB_PATH = os.path.expanduser("~/.quantlive_subs.db")
POLL_OFFSET = 0


# ---------- DB ----------
def _db():
    cx = sqlite3.connect(DB_PATH)
    cx.execute("""CREATE TABLE IF NOT EXISTS subs (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        plan TEXT,
        expires_at REAL,
        status TEXT,
        paid_amount REAL,
        approved_by INTEGER,
        created_at REAL
    )""")
    cx.commit()
    return cx


def get_sub(user_id: int) -> dict | None:
    cx = _db()
    row = cx.execute("SELECT * FROM subs WHERE user_id=?", (user_id,)).fetchone()
    cx.close()
    if not row:
        return None
    cols = ["user_id", "username", "plan", "expires_at", "status", "paid_amount", "approved_by", "created_at"]
    return dict(zip(cols, row))


def upsert_sub(user_id: int, username: str, plan: str, days: int, amount: float, approved_by: int = None):
    cx = _db()
    expires = time.time() + days * 86400
    cx.execute(
        """INSERT INTO subs (user_id, username, plan, expires_at, status, paid_amount, approved_by, created_at)
           VALUES (?,?,?,?,?,?,?,?)
           ON CONFLICT(user_id) DO UPDATE SET
             plan=excluded.plan, expires_at=excluded.expires_at, status='active',
             paid_amount=excluded.paid_amount, approved_by=excluded.approved_by,
             created_at=excluded.created_at""",
        (user_id, username, plan, expires, "active", amount, approved_by, time.time()),
    )
    cx.commit()
    cx.close()


def set_status(user_id: int, status: str):
    cx = _db()
    cx.execute("UPDATE subs SET status=? WHERE user_id=?", (status, user_id))
    cx.commit()
    cx.close()


def list_subs() -> list:
    cx = _db()
    rows = cx.execute("SELECT user_id, username, plan, expires_at, status FROM subs").fetchall()
    cx.close()
    return rows


def expired_subs() -> list:
    cx = _db()
    now = time.time()
    rows = cx.execute(
        "SELECT user_id FROM subs WHERE status='active' AND expires_at < ?", (now,)
    ).fetchall()
    cx.close()
    return [r[0] for r in rows]


# ---------- Helpers Telegram ----------
async def _tg(token: str, method: str, **kwargs):
    async with httpx.AsyncClient(timeout=15) as c:
        return await c.post(f"https://api.telegram.org/bot{token}/{method}", json=kwargs)


async def _tg_photo(token: str, chat_id: int, png: bytes, caption: str) -> None:
    """Envoie une photo (QR code PNG) via multipart/form-data. Fail-open."""
    if not token:
        return
    try:
        async with httpx.AsyncClient(timeout=20) as c:
            await c.post(
                f"https://api.telegram.org/bot{token}/sendPhoto",
                data={"chat_id": str(chat_id), "caption": caption, "parse_mode": "HTML"},
                files={"photo": ("qr.png", png, "image/png")},
            )
    except Exception as e:
        logger.warning("subscription_bot: sendPhoto echec: {}", e)


def _fmt_exp(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


# ---------- QR code ----------
def _make_qr(text: str) -> bytes | None:
    """Genere un QR code PNG (bytes) pour `text`. None si qrcode/Pillow absent."""
    try:
        import io

        import qrcode
    except Exception as e:
        logger.warning("subscription_bot: generation QR indisponible ({})", e)
        return None
    try:
        img = qrcode.make(text, box_size=10, border=2)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception as e:
        logger.warning("subscription_bot: generation QR echec: {}", e)
        return None


# ---------- Commandes ----------
async def cmd_pay(chat_id: int, user_id: int, username: str, args: list):
    plan = args[0] if args else "mensuel"
    if plan not in PLANS:
        await _tg(SUB_BOT_TOKEN, "sendMessage", chat_id=chat_id,
                  text=f"❌ Plan inconnu. Plans: {', '.join(PLANS.keys())}")
        return
    days, price = PLANS[plan]
    text = (
        f"💳 <b>Abonnement {plan}</b> — {price} USDT ({days} jours)\n\n"
        f"Réseau: <b>{USDT_NETWORK}</b>\n"
        f"Adresse: <code>{USDT_ADDRESS}</code>\n\n"
        f"⚠️ Envoie <b>exactement {price} USDT</b>, puis contacte @redou (admin) "
        f"avec la capture du hash de transaction.\n"
        f"L'admin validera manuellement et t'ajoutera au groupe.\n\n"
        f"📋 Ta réf: <code>#{user_id}</code>"
    )
    await _tg(SUB_BOT_TOKEN, "sendMessage", chat_id=chat_id, text=text, parse_mode="HTML")
    # QR code (scan & pay) : envoye en photo si la generation est disponible.
    # Payload reseau-aware : URI EIP-681 pour ERC20, adresse brute pour TRC20.
    _qr_payload = USDT_ADDRESS
    if USDT_NETWORK.upper() in ("ERC20", "ERC-20", "ETH", "ETHEREUM"):
        _qr_payload = f"ethereum:{USDT_ADDRESS}"
    png = _make_qr(_qr_payload)
    if png:
        await _tg_photo(
            SUB_BOT_TOKEN,
            chat_id,
            png,
            caption=f"📱 Scanne pour payer <b>{price} USDT</b> ({USDT_NETWORK})",
        )


async def cmd_status(chat_id: int, user_id: int):
    s = get_sub(user_id)
    if not s or s["status"] != "active":
        await _tg(SUB_BOT_TOKEN, "sendMessage", chat_id=chat_id,
                  text="❌ Aucun abonnement actif. Tape /pay pour t'abonner.")
        return
    await _tg(SUB_BOT_TOKEN, "sendMessage", chat_id=chat_id,
              text=f"✅ Abonnement <b>{s['plan']}</b> actif\n"
                   f"Expire le: {_fmt_exp(s['expires_at'])}\n"
                   f"Montant payé: {s['paid_amount']} USDT",
              parse_mode="HTML")


async def cmd_approve(args: list, by: int):
    if not args:
        return "❌ Usage: /approve <user_id> [plan]"
    uid = int(args[0])
    plan = args[1] if len(args) > 1 else "mensuel"
    days, price = PLANS.get(plan, (30, 50))
    upsert_sub(uid, "", plan, days, price, approved_by=by)
    # ajoute au groupe via le bot de signaux (admin)
    await _tg(SIGNALS_TOKEN, "unbanChatMember", chat_id=GROUP_CHAT_ID, user_id=uid)
    await _tg(SIGNALS_TOKEN, "inviteLink", chat_id=GROUP_CHAT_ID)  # refresh
    return f"✅ User {uid} approuvé ({plan}). Expiration dans {days}j. Ajouté au groupe."


async def cmd_deny(args: list):
    if not args:
        return "❌ Usage: /deny <user_id>"
    uid = int(args[0])
    set_status(uid, "denied")
    await _tg(SIGNALS_TOKEN, "banChatMember", chat_id=GROUP_CHAT_ID, user_id=uid)
    return f"⛔ User {uid} refusé et exclu du groupe."


async def cmd_list() -> str:
    rows = list_subs()
    if not rows:
        return "Aucun abonnement."
    lines = [f"👥 {len(rows)} abonnement(s):"]
    for uid, uname, plan, exp, status in rows:
        lines.append(f"• {uid} (@{uname}) — {plan} — {status} — exp {_fmt_exp(exp)}")
    return "\n".join(lines)


async def cmd_kick_expired():
    expired = expired_subs()
    for uid in expired:
        set_status(uid, "expired")
        try:
            await _tg(SIGNALS_TOKEN, "banChatMember", chat_id=GROUP_CHAT_ID, user_id=uid)
            await _tg(SIGNALS_TOKEN, "unbanChatMember", chat_id=GROUP_CHAT_ID, user_id=uid)
        except Exception as e:
            logger.warning("kick expired {} echec: {}", uid, e)
    return len(expired)


# ---------- Poll loop ----------
async def poll_loop() -> None:
    global POLL_OFFSET
    if not SUB_BOT_TOKEN:
        logger.warning("subscription_bot: SUBSCRIPTION_BOT_TOKEN manquant, desactive")
        return
    logger.info("subscription_bot: demarrage polling")
    async with httpx.AsyncClient(timeout=30) as client:
        while True:
            try:
                r = await client.get(
                    f"https://api.telegram.org/bot{SUB_BOT_TOKEN}/getUpdates",
                    params={"offset": POLL_OFFSET, "timeout": 25},
                )
                data = r.json()
                for upd in data.get("result", []):
                    POLL_OFFSET = upd["update_id"] + 1
                    msg = upd.get("message") or upd.get("edited_message") or {}
                    uid = msg.get("from", {}).get("id")
                    cid = msg.get("chat", {}).get("id")
                    uname = msg.get("from", {}).get("username", "")
                    text = msg.get("text", "") or ""
                    if not text.startswith("/"):
                        continue
                    parts = text[1:].split()
                    cmd = parts[0].lower()
                    args = parts[1:]
                    if uid == ADMIN_USER_ID:
                        if cmd == "approve":
                            await _tg(SUB_BOT_TOKEN, "sendMessage", chat_id=cid, text=await cmd_approve(args, uid))
                        elif cmd == "deny":
                            await _tg(SUB_BOT_TOKEN, "sendMessage", chat_id=cid, text=await cmd_deny(args))
                        elif cmd == "list":
                            await _tg(SUB_BOT_TOKEN, "sendMessage", chat_id=cid, text=await cmd_list())
                        elif cmd == "kick":
                            n = await cmd_kick_expired()
                            await _tg(SUB_BOT_TOKEN, "sendMessage", chat_id=cid, text=f"✅ {n} expiré(s) kické(s)")
                        elif cmd == "pay":
                            await cmd_pay(cid, uid, uname, args)
                        elif cmd == "status":
                            await cmd_status(cid, uid)
                        elif cmd == "renew":
                            await cmd_pay(cid, uid, uname, args or ["mensuel"])
                        elif cmd == "start":
                            await _tg(SUB_BOT_TOKEN, "sendMessage", chat_id=cid,
                                      text="🤖 Bot d'abonnement ORUSDTrade\n/pay — s'abonner\n/status — mon abonnement")
                    else:
                        # utilisateur normal
                        if cmd == "pay":
                            await cmd_pay(cid, uid, uname, args)
                        elif cmd == "status":
                            await cmd_status(cid, uid)
                        elif cmd == "renew":
                            await cmd_pay(cid, uid, uname, args or ["mensuel"])
                        elif cmd == "start":
                            await _tg(SUB_BOT_TOKEN, "sendMessage", chat_id=cid,
                                      text="🤖 Bot d'abonnement ORUSDTrade\n/pay — s'abonner\n/status — mon abonnement")
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.warning("subscription_bot poll error: {}", e)
                await asyncio.sleep(5)


# tache planifiee: kick les expires toutes les 6h
async def scheduled_kick():
    while True:
        await asyncio.sleep(6 * 3600)
        try:
            n = await cmd_kick_expired()
            if n:
                logger.info("subscription_bot: {} expires kickes", n)
        except Exception as e:
            logger.warning("scheduled_kick echec: {}", e)


# ---------- Point d'entree standalone ----------
async def _main() -> None:
    """Lance poll_loop + scheduled_kick en parallele (usage standalone)."""
    await asyncio.gather(poll_loop(), scheduled_kick())


def main() -> None:
    if not SUB_BOT_TOKEN:
        logger.warning(
            "subscription_bot: SUBSCRIPTION_BOT_TOKEN manquant — bot desactive "
            "(renseigne-le dans l'environnement / QuantLive/.env)"
        )
        return
    asyncio.run(_main())


if __name__ == "__main__":
    main()
