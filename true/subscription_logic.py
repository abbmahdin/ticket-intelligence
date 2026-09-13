"""Logic d'abonnement payant ORUSDTrade — integree au bot ORUSDTradeBOT existant.

Reutilise telegram_bot_token (deja admin du groupe) => pas besoin de 2e bot.
Paiement: Stripe (Visa/MC/Bancontact) via Payment Link + Crypto USDT (manuel).

Commandes (dans le groupe):
  /pay           -> lien carte (bouton) + adresse USDT  [tous]
  /status        -> etat de l'abonnement de l'user       [tous]
  /approve uid   -> valide + ajoute au groupe            [admin]
  /deny uid      -> refuse + kick                        [admin]
  /list          -> liste des abonnements                [admin]
  /kick          -> kick les expires                     [admin]
"""

import sys as _sys
# subscription_logic.py is imported by BOTH:
#   - QuantLive FastAPI app (cwd=/home/redou/QuantLive/ — can resolve
#     ``from app._path_compat import …`` below)
#   - standalone Telegram bot handler (cwd=/home/redou — cannot find an
#     ``app.*`` module on sys.path, falls through to the local hardcoded
#     /home/redou inject below)
# See ``app._path_compat`` for the canonical helper + the shadow-risk note.
if "/home/redou" not in _sys.path:
    _sys.path.insert(0, "/home/redou")
try:
    from app._path_compat import setup_repo_path as _setup_repo_path  # type: ignore
    _setup_repo_path()  # idempotent — local inject above already covered it
except ImportError:
    pass  # Not in a QuantLive cwd — local inject above already handled it.

import os
import time
import sqlite3
import httpx
from loguru import logger

try:
    from app.config import get_settings
    _S = get_settings()
    SIGNALS_TOKEN = getattr(_S, "telegram_bot_token", "") or os.environ.get("TELEGRAM_BOT_TOKEN", "")
    GROUP_CHAT_ID = int(getattr(_S, "telegram_chat_id", "") or os.environ.get("TELEGRAM_CHAT_ID", "-1003792796980"))
except Exception:
    SIGNALS_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    GROUP_CHAT_ID = int(os.environ.get("TELEGRAM_CHAT_ID", "-1003792796980"))

ADMIN_USER_ID = int(os.environ.get("SUBSCRIPTION_ADMIN_ID", "6459871864"))
USDT_ADDRESS = os.environ.get("SUBSCRIPTION_USDT_ADDRESS", "")
USDT_NETWORK = os.environ.get("SUBSCRIPTION_USDT_NETWORK", "TRC20")

PLANS = {
    "mensuel": (30, 50),
    "trimestriel": (90, 130),
    "annuel": (365, 450),
}

DB_PATH = os.path.expanduser("~/.quantlive_subs.db")


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


def get_sub(user_id):
    cx = _db()
    row = cx.execute("SELECT * FROM subs WHERE user_id=?", (user_id,)).fetchone()
    cx.close()
    if not row:
        return None
    cols = ["user_id", "username", "plan", "expires_at", "status", "paid_amount", "approved_by", "created_at"]
    return dict(zip(cols, row))


def upsert_sub(user_id, username, plan, days, amount, approved_by=None):
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


def set_status(user_id, status):
    cx = _db()
    cx.execute("UPDATE subs SET status=? WHERE user_id=?", (status, user_id))
    cx.commit()
    cx.close()


def list_subs():
    cx = _db()
    rows = cx.execute("SELECT user_id, username, plan, expires_at, status FROM subs").fetchall()
    cx.close()
    return rows


def expired_subs():
    cx = _db()
    now = time.time()
    rows = cx.execute("SELECT user_id FROM subs WHERE status='active' AND expires_at < ?", (now,)).fetchall()
    cx.close()
    return [r[0] for r in rows]


def _fmt_exp(ts):
    from datetime import datetime, timezone
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


async def _tg(token, method, **kw):
    async with httpx.AsyncClient(timeout=15) as c:
        return await c.post(f"https://api.telegram.org/bot{token}/{method}", json=kw)


# --- Stripe Payment Link ---
async def _stripe_link(plan, user_id):
    # Canonical: app.services.payments (if migrated into QuantLive/app/services/).
    # Backward-compat: top-level /home/redou/payments.py (still used by the
    # standalone bot handler and by the new QuantLive/app/api/stripe_webhook).
    try:
        from app.services.payments import create_payment_link
    except ImportError:
        from payments import create_payment_link
    return await create_payment_link(plan, user_id)


async def cmd_pay_public(chat_id, user_id, raw_text):
    parts = raw_text[1:].split()
    plan = parts[1] if len(parts) > 1 else "mensuel"
    if plan not in PLANS:
        await _tg(SIGNALS_TOKEN, "sendMessage", chat_id=chat_id,
                  text=f"❌ Plan inconnu. Plans: {', '.join(PLANS.keys())}")
        return
    days, price = PLANS[plan]
    link = await _stripe_link(plan, user_id)
    if link:
        kb = {"inline_keyboard": [[{"text": "💳 Payer par carte (Visa/MC/Bancontact)", "url": link}]]}
        text = (
            f"💳 <b>Abonnement {plan}</b> — {price} USDT ({days} jours)\n\n"
            f"🟢 <b>Carte</b> (Visa/Mastercard/Bancontact) : clique le bouton.\n"
            f"Le groupe est débloqué auto après paiement.\n\n"
            f"🟡 <b>Ou crypto USDT</b> ({USDT_NETWORK}) :\n"
            f"<code>{USDT_ADDRESS}</code>\nEnvoie {price} USDT puis contacte @redou avec le hash.\n\n"
            f"📋 Réf: <code>#{user_id}</code>"
        )
        await _tg(SIGNALS_TOKEN, "sendMessage", chat_id=chat_id, text=text, parse_mode="HTML", reply_markup=kb)
    else:
        text = (
            f"💳 <b>Abonnement {plan}</b> — {price} USDT ({days} jours)\n\n"
            f"Réseau: <b>{USDT_NETWORK}</b>\n<code>{USDT_ADDRESS}</code>\n\n"
            f"Envoie {price} USDT puis contacte @redou avec le hash de tx.\n"
            f"📋 Réf: <code>#{user_id}</code>"
        )
        await _tg(SIGNALS_TOKEN, "sendMessage", chat_id=chat_id, text=text, parse_mode="HTML")


async def cmd_status_public(chat_id, user_id):
    s = get_sub(user_id)
    if not s or s["status"] != "active":
        await _tg(SIGNALS_TOKEN, "sendMessage", chat_id=chat_id,
                  text="❌ Aucun abonnement actif. Tape /pay pour t'abonner.")
        return
    await _tg(SIGNALS_TOKEN, "sendMessage", chat_id=chat_id,
              text=f"✅ Abonnement <b>{s['plan']}</b> actif\nExpire le: {_fmt_exp(s['expires_at'])}\nMontant: {s['paid_amount']} USDT",
              parse_mode="HTML")


async def cmd_admin(chat_id, user_id, cmd, args):
    if user_id != ADMIN_USER_ID:
        return
    if cmd == "approve":
        if not args:
            await _tg(SIGNALS_TOKEN, "sendMessage", chat_id=chat_id, text="❌ /approve <user_id> [plan]")
            return
        uid = int(args[0])
        plan = args[1] if len(args) > 1 else "mensuel"
        days, price = PLANS.get(plan, (30, 50))
        upsert_sub(uid, "", plan, days, price, approved_by=user_id)
        await _tg(SIGNALS_TOKEN, "unbanChatMember", chat_id=GROUP_CHAT_ID, user_id=uid)
        await _tg(SIGNALS_TOKEN, "sendMessage", chat_id=chat_id,
                  text=f"✅ User {uid} approuvé ({plan}). Expire dans {days}j.")
    elif cmd == "deny":
        if not args:
            return
        uid = int(args[0])
        set_status(uid, "denied")
        await _tg(SIGNALS_TOKEN, "banChatMember", chat_id=GROUP_CHAT_ID, user_id=uid)
        await _tg(SIGNALS_TOKEN, "sendMessage", chat_id=chat_id, text=f"⛔ User {uid} refusé + exclu.")
    elif cmd == "list":
        rows = list_subs()
        if not rows:
            await _tg(SIGNALS_TOKEN, "sendMessage", chat_id=chat_id, text="Aucun abonnement.")
            return
        lines = [f"👥 {len(rows)} abo:"]
        for uid, uname, plan, exp, status in rows:
            lines.append(f"• {uid} (@{uname}) — {plan} — {status}")
        await _tg(SIGNALS_TOKEN, "sendMessage", chat_id=chat_id, text="\n".join(lines))
    elif cmd == "kick":
        expired = expired_subs()
        for uid in expired:
            set_status(uid, "expired")
            try:
                await _tg(SIGNALS_TOKEN, "banChatMember", chat_id=GROUP_CHAT_ID, user_id=uid)
                await _tg(SIGNALS_TOKEN, "unbanChatMember", chat_id=GROUP_CHAT_ID, user_id=uid)
            except Exception:
                pass
        await _tg(SIGNALS_TOKEN, "sendMessage", chat_id=chat_id, text=f"✅ {len(expired)} expiré(s) kické(s)")


async def scheduled_kick():
    while True:
        await asyncio_sleep()
        try:
            n = len(expired_subs())
            for uid in expired_subs():
                set_status(uid, "expired")
                await _tg(SIGNALS_TOKEN, "banChatMember", chat_id=GROUP_CHAT_ID, user_id=uid)
                await _tg(SIGNALS_TOKEN, "unbanChatMember", chat_id=GROUP_CHAT_ID, user_id=uid)
            if n:
                logger.info("subs: {} expires kickes", n)
        except Exception as e:
            logger.warning("scheduled_kick echec: {}", e)


async def asyncio_sleep():
    import asyncio
    await asyncio.sleep(6 * 3600)
