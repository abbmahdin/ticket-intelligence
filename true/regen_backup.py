p_backup = "/home/redou/.quantlive-secrets-backup/.env.backup"
p_env = "/home/redou/QuantLive/.env"

# Clés PERSO strictement hors backup (souvenir utilisateur : jamais réaffichées).
# Les SUBSCRIPTION_BANK_*/SUBSCRIPTION_CDC_* ont été retirées de .env (virement
# bancaire/crypto.com supprimés, remplacés par Stripe + USDT).
EXCLUDE_EXACT = {
    "SUBSCRIPTION_USDT_ADDRESS",
    "SUBSCRIPTION_USDT_NETWORK",
}

lines = []
seen = set()
with open(p_env) as f:
    for line in f:
        line = line.rstrip("\n")
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key = line.split("=", 1)[0].strip()
        if key in seen:
            continue
        if key in EXCLUDE_EXACT:
            continue
        seen.add(key)
        lines.append(line)

header = "# QuantLive/ORUSDTrade secrets backup — mis a jour automatiquement\n"
header += "# Cible: pas de coordonnees bancaires/crypto perso (hors backup par securite)\n"
with open(p_backup, "w") as f:
    f.write(header)
    f.write("\n".join(lines) + "\n")

print(f"backup regenere: {len(lines)} cles")
print("EXCLU (perso):", sorted(EXCLUDE_EXACT))
# verifie Mini App present
import subprocess
r = subprocess.run(["grep", "-c", "MINIAPP_", p_backup], capture_output=True, text=True)
print("MINIAPP_ dans backup:", r.stdout.strip())
