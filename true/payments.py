"""Paiements ORUSDTrade: Stripe (Visa/Mastercard/Bancontact) + Crypto USDT.

- Stripe Payment Links: cree un lien de paiement par plan, l'utilisateur paie
  par carte (Visa/MC/Bancontact auto-geres par Stripe). Webhook Stripe ->
  abonnement active automatiquement (plus de validation manuelle pour la carte).
- Crypto USDT: validation manuelle par l'admin (comme avant).

Configuration .env:
  STRIPE_SECRET_KEY=sk_live_...
  STRIPE_WEBHOOK_SECRET=whsec_...
  STRIPE_PRICE_MENSUEL=price_xxx   (cree dans Stripe, mode paiement unique)
  STRIPE_PRICE_TRIMESTRIEL=price_xxx
  STRIPE_PRICE_ANNUEL=price_xxx
  SUBSCRIPTION_USDT_ADDRESS=...
"""

import os
import time
import httpx
from loguru import logger

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRICES = {
	"mensuel": os.environ.get("STRIPE_PRICE_MENSUEL", ""),
	"trimestriel": os.environ.get("STRIPE_PRICE_TRIMESTRIEL", ""),
	"annuel": os.environ.get("STRIPE_PRICE_ANNUEL", ""),
}
# Plans locaux (pour duree + fallback): nom -> (jours, prix USDT)
PLANS = {
	"mensuel": (30, 50),
	"trimestriel": (90, 130),
	"annuel": (365, 450),
}


async def create_payment_link(plan: str, user_id: int) -> str | None:
	"""Cree un Stripe Payment Link pour le plan et y attache le user_id (metadata)."""
	price = STRIPE_PRICES.get(plan)
	if not STRIPE_SECRET_KEY or not price:
		return None
	try:
		async with httpx.AsyncClient(timeout=20) as c:
			# 1) cree une session de paiement (mode payment, unique)
			r = await c.post(
				"https://api.stripe.com/v1/checkout/sessions",
				auth=(STRIPE_SECRET_KEY, ""),
				data={
					"mode": "payment",
					"line_items[0][price]": price,
					"line_items[0][quantity]": "1",
					"success_url": "https://t.me/ORUSDTradeBot?start=paid",
					"cancel_url": "https://t.me/ORUSDTradeBot",
					"metadata[user_id]": str(user_id),
					"metadata[plan]": plan,
					"payment_method_types[]": "card",
					# Bancontact est dispo automatiquement si l'utilisateur est BE
				},
			)
			sess = r.json()
			if "url" not in sess:
				logger.warning("stripe session echec: {}", sess)
				return None
			return sess["url"]
	except Exception as e:
		logger.warning("create_payment_link echec: {}", e)
		return None


def verify_webhook(payload: bytes, sig: str) -> dict | None:
	"""Verifie la signature du webhook Stripe (header Stripe-Signature).

	Returns the parsed event dict if HMAC verifies, else ``None`` with a
	WARNING breadcrumb per failure mode (6 distinct paths) so silent
	400-storms after a redeploy or env drift stay visible in logs.
	"""
	import hmac, hashlib
	if not STRIPE_WEBHOOK_SECRET:
		logger.warning(
			"stripe webhook refused: STRIPE_WEBHOOK_SECRET not configured "
			"(every Stripe call will 400 until the env var is set)"
		)
		return None
	if not sig:
		logger.warning(
			"stripe webhook refused: missing Stripe-Signature header "
			"(client is likely behind a WAF/proxy that strips it)"
		)
		return None
	try:
		parts = dict(x.split("=", 1) for x in sig.split(","))
	except Exception as e:
		logger.warning("stripe webhook refused: malformed signature header ({})", e)
		return None
	ts = parts.get("t", "")
	try:
		expected = hmac.new(
			STRIPE_WEBHOOK_SECRET.encode(),
			f"{ts}.".encode() + payload,
			hashlib.sha256,
		).hexdigest()
	except Exception as e:
		logger.warning("stripe webhook refused: HMAC compute failed ({})", e)
		return None
	if not hmac.compare_digest(parts.get("v1", ""), expected):
		logger.warning(
			"stripe webhook refused: HMAC mismatch (possible spoof or rotated secret)"
		)
		return None
	try:
		return __import__("json").loads(payload.decode())
	except Exception as e:
		logger.warning("stripe webhook refused: payload is not valid JSON ({})", e)
		return None
