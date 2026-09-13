p_backup = "/home/redou/.quantlive-secrets-backup/.env.backup"
p_env = "/home/redou/QuantLive/.env"

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
        seen.add(key)
        lines.append(line)

header = "# QuantLive/ORUSDTrade secrets backup — mis a jour (AVEC coordonnees crypto perso)\n"
with open(p_backup, "w") as f:
    f.write(header)
    f.write("\n".join(lines) + "\n")

print(f"backup regenere: {len(lines)} cles (crypto perso INCLUSES)")
for k in ("SUBSCRIPTION_USDT_ADDRESS",):
    print(k, ":", "OK" if any(l.startswith(k+"=") for l in lines) else "MANQUANT")
