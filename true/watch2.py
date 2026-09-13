"""Diagnostic détaillé du rollover 12:06-12:10 UTC.

1. Qui écrit /tmp/nochase_monitor.log + lignes nouveau format (ISO) présentes.
2. Cycle de vie des tickets 52738911 (SELL fermée) et 52739210 (BUY ouverte).
3. slots.json : quel bot porte la BUY 52739210.
"""
import datetime
import glob
import json
import os
import subprocess
import time

NOW = datetime.datetime.now(datetime.timezone.utc)
CUTOFF = (NOW - datetime.timedelta(minutes=18)).timestamp()


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


print("NOW UTC:", NOW.strftime("%H:%M:%S"), "| cutoff:", hm(CUTOFF), "\n")

# 1) nochase log : qui écrit, et lignes nouveau format (commencent par une date ISO)
p = "/tmp/nochase_monitor.log"
print("=== /tmp/nochase_monitor.log ===")
print("writers (fuser/lsof):", end=" ")
try:
    out = subprocess.run(["fuser", p], capture_output=True, text=True, timeout=10)
    print(out.stdout.strip() or "(aucun process ne tient le fichier)")
except Exception as e:
    print("(fuser indispo:", e, ")")
if os.path.exists(p):
    lignes = [l.rstrip() for l in open(p, errors="replace") if l.strip()]
    iso = [l for l in lignes if l[:1].isdigit() and "-" in l[:12]]
    print(f"total={len(lignes)} | lignes nouveau format ISO={len(iso)}")
    for l in iso[-10:]:
        print("  ISO:", l[:160])
    print("  mtime:", datetime.datetime.fromtimestamp(os.path.getmtime(p), datetime.timezone.utc).strftime("%H:%M:%S"))
print()

# 2) tickets
print("=== tickets 52738911 / 52739210 dans les journaux (depuis cutoff) ===")
for f in sorted(glob.glob("logs/micro*-trademax.jsonl")):
    bot = f.split("/")[-1].replace(".jsonl", "")
    hits = []
    for line in open(f, errors="replace"):
        try:
            d = json.loads(line)
        except Exception:
            continue
        ts = ts_of(d)
        if ts is None or ts < CUTOFF:
            continue
        s = json.dumps(d, ensure_ascii=False)
        if "52738911" in s or "52739210" in s:
            ev = d.get("event")
            if ev in ("shadow_open", "shadow_close", "adoption", "reconciliation",
                      "position_apparue", "slot_libre", "orphelin_ferme", "sortie_non_emise"):
                hits.append(
                    f"{hm(ts)} [{ev}] {d.get('direction','')} motif={d.get('motif','')} "
                    f"ticket={d.get('ticket','')} slot={d.get('slot_id','')} "
                    f"R={d.get('resultat_r','')} pts={d.get('resultat_points','')}"
                )
    if hits:
        print(f"-- {bot}:")
        for h in hits[-8:]:
            print("   ", h[:170])
print()

# 3) slots.json
for sj in glob.glob("data/micro/slots*.json"):
    pass
print("=== slots.json files ===")
for sj in glob.glob("data/**/slots*.json", recursive=True):
    mtime = datetime.datetime.fromtimestamp(os.path.getmtime(sj), datetime.timezone.utc).strftime("%H:%M:%S")
    try:
        d = json.load(open(sj))
        slots = d.get("slots") if isinstance(d, dict) else d
        print(f"-- {sj} (mtime {mtime})")
        if isinstance(slots, dict):
            for sid, s in slots.items():
                if s:
                    print(f"   slot {sid}: {s.get('direction')} ticket={s.get('ticket')} "
                          f"entry={s.get('entry')} sl={s.get('sl')} tp={s.get('tp')}")
        elif isinstance(slots, list):
            for s in slots:
                print(f"   slot: {s}")
    except Exception as e:
        print(f"-- {sj}: (illisible {e})")
