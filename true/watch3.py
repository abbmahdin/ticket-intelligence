"""Watch vivant : refus pullback strict + closes REVERSAL_M5 + opens + état.

Dedup global par clé (bot, event, ts, slot). Bounded 8 min par run.
"""
import datetime
import glob
import json
import os
import time

DEBUT = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=2)).timestamp()


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


def hm(ts):
    return time.strftime("%H:%M:%S", time.gmtime(ts)) if ts else "?"


def scan(seen):
    out = []
    p = "/tmp/nochase_monitor.log"
    if os.path.exists(p):
        for l in open(p, errors="replace"):
            l = l.rstrip()
            if l[:1].isdigit() and "-" in l[:12] and "PULLBACK_INSUFFISANT" in l:
                if ("log", l) not in seen:
                    seen.add(("log", l))
                    out.append("LOG-PB: " + l[:170])
    for f in sorted(glob.glob("logs/micro*-trademax.jsonl")):
        bot = f.split("/")[-1].replace(".jsonl", "")
        for line in open(f, errors="replace"):
            try:
                d = json.loads(line)
            except Exception:
                continue
            ts = ts_of(d)
            if ts is None or ts < DEBUT:
                continue
            ev = d.get("event")
            if ev in ("shadow_open", "shadow_close", "sortie_reportee", "adoption",
                      "position_apparue", "reversal_pullback", "tp1_hit", "be_live_atteint"):
                motif = d.get("motif", "")
                k = (bot, ev, ts, d.get("slot_id"), motif)
                if k in seen:
                    continue
                seen.add(k)
                detail = f"motif={motif} R={d.get('resultat_r')} pts={d.get('resultat_points')}"
                if motif == "reversal_m5":
                    out.append(f"*** REVERSAL_M5 [{bot}] {hm(ts)} slot={d.get('slot_id')} {d.get('direction')} {detail}")
                elif ev == "shadow_open":
                    out.append(f"OPEN [{bot}] {hm(ts)} slot={d.get('slot_id')} {d.get('direction')} entree={d.get('entree')}")
                elif ev == "shadow_close":
                    out.append(f"CLOSE [{bot}] {hm(ts)} slot={d.get('slot_id')} {d.get('direction')} {detail}")
            elif ev == "candidat":
                for r in d.get("refusals") or []:
                    if "pullback strict M5" in str(r):
                        k = ("pb", bot, ts)
                        if k not in seen:
                            seen.add(k)
                            out.append(f"REFUS-PB [{bot}] {hm(ts)} {d.get('direction')}: {str(r)[:130]}")
    return out


seen = set()
fin = time.time() + 480  # 8 min max
print("Watch", datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M:%S"), "UTC — 8 min max")
while time.time() < fin:
    for l in scan(seen):
        print(l, flush=True)
    t = time.strftime("%H:%M:%S", time.gmtime())
    p = "/mnt/c/Users/redou/AppData/Roaming/MetaQuotes/Terminal/Common/Files/quantlive_mt4_trademax-1_status.json"
    if os.path.exists(p):
        d = json.load(open(p))
        pos = d.get("positions") or []
        slots_txt = []
        for sj in glob.glob("data/micro-*-trademax/slots.json"):
            bot = sj.split("micro-")[1].split("/")[0]
            try:
                dd = json.load(open(sj))
                sl = dd.get("slots") or {}
                for sid, s in sl.items():
                    if s:
                        slots_txt.append(f"{bot}:s{sid}:{s.get('direction')}:t{s.get('ticket')}")
            except Exception:
                pass
        print(f"[{t}] EA pos={len(pos)} | {' '.join(slots_txt) or '-'}", flush=True)
    time.sleep(60)

print("=== fin du run ===")
for l in scan(seen):
    print(l, flush=True)
