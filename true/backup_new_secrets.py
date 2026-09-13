import os, json, datetime

proj = "/home/redou/QuantLive"
bkp = "/home/redou/.quantlive-secrets-backup/.env.backup"

# ---- lire .env actuel ----
env = {}
for line in open(os.path.join(proj, ".env"), encoding="utf-8"):
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, _, v = line.partition("=")
    env[k] = v

# ---- lire mt5_accounts.json ----
mt5 = {}
try:
    raw = json.load(open(os.path.join(proj, "mt5_accounts.json"), encoding="utf-8"))
    for a in raw.get("accounts", []):
        if a.get("enabled"):
            mt5["MT5_ACCOUNT_LOGIN"] = a["login"]
            mt5["MT5_ACCOUNT_PASSWORD"] = a["password"]
            mt5["MT5_ACCOUNT_SERVER"] = a["server"]
            mt5["MT5_ACCOUNT_NAME"] = a["name"]
except Exception as e:
    print("mt5_accounts.json read error:", e)

# ---- nouvelles cles a sauvegarder ----
new_keys = {
    "MT5_API_KEY": env.get("MT5_API_KEY", ""),
    "MT5_ENABLED": env.get("MT5_ENABLED", ""),
    "MT5_MODE": env.get("MT5_MODE", ""),
    "MT5_SYMBOL": env.get("MT5_SYMBOL", ""),
    "MT5_MAX_RISK": env.get("MT5_MAX_RISK", ""),
    "MT5_MAX_DAILY_LOSS": env.get("MT5_MAX_DAILY_LOSS", ""),
    "MT5_MAGIC": env.get("MT5_MAGIC", ""),
    "MT5_POLL_SECONDS": env.get("MT5_POLL_SECONDS", ""),
    "MINIAPP_SECRET": env.get("MINIAPP_SECRET", ""),
}
new_keys.update(mt5)

# ---- lire backup existant ----
bkp_env = {}
bkp_lines = []
for line in open(bkp, encoding="utf-8"):
    bkp_lines.append(line.rstrip("\n"))
    if line.strip() and not line.startswith("#") and "=" in line:
        k, _, v = line.partition("=")
        bkp_env[k] = v

out = []
changed = False
for k, v in new_keys.items():
    if not v:
        continue
    if bkp_env.get(k) == v:
        continue
    out.append(f"{k}={v}")
    changed = True

if not changed:
    print("backup deja a jour (aucune nouvelle donnee)")
else:
    stamp = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H%M%SZ")
    with open(bkp, "a") as f:
        f.write(f"\n# ── MAJ {stamp} (MetaApi + MT5 + MiniApp) ──\n")
        f.write("\n".join(out) + "\n")
    os.chmod(bkp, 0o600)
    print(f"backup mis a jour: {len(out)} entree(s) ajoutee(s)/MAJ")
    for l in out:
        print(" +", l.split("=")[0])

# ---- copier mt5_accounts.json dans le backup chiffre ----
sec_dir = "/home/redou/.quantlive-secrets-backup"
dst = os.path.join(sec_dir, "mt5_accounts.json")
json.dump(raw, open(dst, "w", encoding="utf-8"), indent=2)
os.chmod(dst, 0o600)
print("mt5_accounts.json copie dans backup:", dst)
