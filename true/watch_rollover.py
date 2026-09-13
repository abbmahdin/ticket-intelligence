"""Watch the live rollover after the 12:06 UTC restart (strict-pullback +
REVERSAL_M5 armed). Cutoff = now - 12 min (auto, not hardcoded)."""
import datetime
import glob
import json
import os
import time

NOW = datetime.datetime.now(datetime.timezone.utc)
CUTOFF = (NOW - datetime.timedelta(minutes=12)).timestamp()


def ts_of(d):
    t = d.get("ts")
    if t is None:
        return None
    if isinstance(t, (int, float)):
        return float(t)
    try:
        return datetime.datetime.fromisoformat(str(t).replace("Z", "+00:00")).timestamp()
    except Exception:
        return None


print("NOW UTC:", NOW.strftime("%Y-%m-%d %H:%M:%S"))
print("cutoff:", datetime.datetime.fromtimestamp(CUTOFF, datetime.timezone.utc).strftime("%H:%M:%S"), "UTC\n")

p = "/tmp/nochase_monitor.log"
print("=== /tmp/nochase_monitor.log ===")
if os.path.exists(p):
    lignes = [l for l in open(p, errors="replace") if l.strip()]
    print(f"total={len(lignes)} lignes; 15 dernières:")
    for l in lignes[-15:]:
        print(" ", l.rstrip()[:160])
else:
    print("ABSENT")
print()

print("=== journals micro*-trademax depuis cutoff ===")
for f in sorted(glob.glob("logs/micro*-trademax.jsonl")):
    bot = f.split("/")[-1].replace(".jsonl", "")
    reversal, refus_pb, closes = [], [], []
    cand = 0
    for line in open(f, errors="replace"):
        try:
            d = json.loads(line)
        except Exception:
            continue
        ts = ts_of(d)
        if ts is None or ts < CUTOFF:
            continue
        ev = d.get("event")
        hm = time.strftime("%H:%M:%S", time.gmtime(ts))
        if ev == "shadow_close":
            closes.append(
                f"{hm} slot={d.get('slot_id')} {d.get('direction')} motif={d.get('motif')} "
                f"R={d.get('resultat_r')} pts={d.get('resultat_points')}"
            )
            if d.get("motif") == "reversal_m5":
                reversal.append(closes[-1])
        elif ev == "candidat":
            cand += 1
            for r in d.get("refusals") or []:
                s = str(r)
                if "pullback strict M5" in s or "PULLBACK_INSUFFISANT" in s:
                    refus_pb.append(f"{hm} {d.get('direction')}: {s[:120]}")
    print(f"-- {bot}: candidats={cand} | closes={len(closes)} | "
          f"reversal_m5={len(reversal)} | refus pullback strict={len(refus_pb)}")
    for c in closes[-6:]:
        print("   CLOSE:", c[:150])
    for r in refus_pb[:6]:
        print("   REFUS PB:", r)
print()

p = "/mnt/c/Users/redou/AppData/Roaming/MetaQuotes/Terminal/Common/Files/quantlive_mt4_trademax-1_status.json"
if os.path.exists(p):
    d = json.load(open(p))
    print("=== EA trademax-1 ===")
    print("connected:", d.get("connected"), "| positions:", d.get("positions_count"))
    for pos in d.get("positions", []):
        print("  pos:", {k: pos.get(k) for k in ("ticket", "type", "volume", "open_price", "sl", "tp", "profit")})
else:
    print("=== EA status absent ===")
