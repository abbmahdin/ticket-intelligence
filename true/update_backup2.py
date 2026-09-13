import os
proj = "/home/redou/QuantLive"
bkp = "/home/redou/.quantlive-secrets-backup/.env.backup"
env_path = os.path.join(proj, ".env")

env = {}
for line in open(env_path):
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, _, v = line.partition("=")
    env[k] = v

# cles a sauvegarder dans le backup
keys = [
    "STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET",
    "STRIPE_PRICE_MENSUEL", "STRIPE_PRICE_TRIMESTRIEL", "STRIPE_PRICE_ANNUEL",
    "OPENROUTER_API_KEY", "KIMI_MODEL",
    "SUBSCRIPTION_USDT_ADDRESS", "SUBSCRIPTION_USDT_NETWORK", "SUBSCRIPTION_ADMIN_ID",
    "QUANTLIVE_TUNNEL_URL",
]

# lit backup existant en dict pour ne pas dupliquer
bkp_env = {}
bkp_lines = []
for line in open(bkp):
    bkp_lines.append(line.rstrip("\n"))
    if line.strip() and not line.startswith("#") and "=" in line:
        k, _, v = line.partition("=")
        bkp_env[k] = v

out = []
changed = False
for k in keys:
    if k not in env or not env[k]:
        continue
    if bkp_env.get(k) == env[k]:
        continue  # deja a jour
    out.append(f"{k}={env[k]}")
    changed = True

# tunnel url pas dans .env -> ajout direct
tunnel = open(os.path.expanduser("~/.quantlive_tunnel_url")).read().strip()
if bkp_env.get("QUANTLIVE_TUNNEL_URL") != tunnel:
    out.append(f"QUANTLIVE_TUNNEL_URL={tunnel}")
    changed = True

if not changed:
    print("backup deja a jour (aucune nouvelle donnee)")
else:
    with open(bkp, "a") as f:
        f.write("\n# ── MAJ " + os.environ.get("DATE", "2026-07-18") + " ──\n")
        f.write("\n".join(out) + "\n")
    print(f"backup mis a jour: {len(out)} entree(s) ajoutee(s)/MAJ")
    for l in out:
        print(" +", l.split("=")[0])
