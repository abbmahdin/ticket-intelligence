import os
proj = "/home/redou/QuantLive"
bkp = "/home/redou/.quantlive-secrets-backup/.env.backup"
env_path = os.path.join(proj, ".env")
tunnel = open(os.path.expanduser("~/.quantlive_tunnel_url")).read().strip()

env = {}
for line in open(env_path):
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, _, v = line.partition("=")
    env[k] = v

keys = ["STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET", "STRIPE_PRICE_MENSUEL",
        "STRIPE_PRICE_TRIMESTRIEL", "STRIPE_PRICE_ANNUEL", "OPENROUTER_API_KEY",
        "SUBSCRIPTION_USDT_ADDRESS", "SUBSCRIPTION_USDT_NETWORK", "SUBSCRIPTION_ADMIN_ID"]

out = ["", "# ── Paiement / Abonnement ORUSDTrade (2026-07-17) ─────────────────────────────"]
for k in keys:
    if k in env:
        out.append(f"{k}={env[k]}")
out.append("# ── Tunnel cloudflared (2026-07-17) ─────")
out.append(f"QUANTLIVE_TUNNEL_URL={tunnel}")

with open(bkp, "a") as f:
    f.write("\n".join(out) + "\n")
print("backup mis a jour:", len(out), "lignes ajoutees")
print("cles:", [l.split("=")[0] for l in out if "=" in l and not l.startswith("#")])
