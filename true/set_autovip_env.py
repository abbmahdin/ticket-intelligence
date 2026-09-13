import os, re
P = "/home/redou/QuantLive/.env"
s = open(P, encoding="utf-8").read() if os.path.exists(P) else ""

# fenetre 30 jours a partir d'aujourd'hui
import time
until_ts = int(time.time()) + 30 * 86400

defaults = {
    "AUTO_VIP_ENABLED": "true",
    "AUTO_VIP_DAYS": "3650",
    "AUTO_VIP_UNTIL": str(until_ts),
    "VIP_PLAN_NAME": "vip",
}
for k, v in defaults.items():
    if re.search(rf"(?m)^{k}=", s):
        s = re.sub(rf"(?m)^{k}=.*$", f"{k}={v}", s)
    else:
        s = s.rstrip("\n") + f"\n{k}={v}\n"

open(P, "w", encoding="utf-8").write(s)
from datetime import datetime, timezone
print("AUTO_VIP set. Fenetre jusqu'a:", datetime.fromtimestamp(until_ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
for k in defaults:
    for line in s.splitlines():
        if line.startswith(k + "="):
            print(" ", line)
