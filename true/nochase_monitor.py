#!/usr/bin/env python3
"""Surveille pendant ~1h les traces candidat des 5 bots trademax-1 pour
confirmer que les refus no-chase bloquent désormais l'ouverture (le filtre
était journal-seulement avant le fix du 2026-09-04). Tick toutes les 60 s.
Sortie : /tmp/nochase_monitor.log
"""
import datetime
import glob
import json
import os
import re
import time

CUTOFF = datetime.datetime(2026, 9, 4, 10, 29, 20, tzinfo=datetime.timezone.utc).timestamp()
LOG = "/tmp/nochase_monitor.log"
LEDGERS = sorted(glob.glob("/home/redou/QuantLive/logs/micro*-trademax.jsonl"))


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


def tick():
    lines = ["=== tick %s ===" % time.strftime("%H:%M:%S UTC", time.gmtime())]
    for f in LEDGERS:
        bot = os.path.basename(f).replace(".jsonl", "")
        n_cand = n_nch = n_open = n_b = n_s = n_none = 0
        derniers = []
        try:
            fh = open(f, errors="replace")
        except OSError:
            continue
        with fh:
            for line in fh:
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                ts = ts_of(d)
                if ts is None or ts < CUTOFF:
                    continue
                e = d.get("event")
                if e == "candidat":
                    n_cand += 1
                    # Le champ m5_tendance n'est PAS journalisé tel quel :
                    # la tendance M5 du cycle vit dans gates.direction_bias.value
                    # ("M5 BUY / sens BUY (VETO…)" ou
                    # "M5 non mesurable / sens BUY (fail-open…)"). Vérifié sur
                    # un événement réel : direction_bias a les clés
                    # [measured, passed, value] — pas de `reason`.
                    mt = None
                    try:
                        db_val = (d.get("gates") or {}).get("direction_bias") or {}
                        db_val = db_val.get("value") if isinstance(db_val, dict) else db_val
                        m = re.search(r"M5\s+(BUY|SELL|non mesurable)", str(db_val))
                        if m:
                            v = m.group(1)
                            if v in ("BUY", "SELL"):
                                mt = v
                    except Exception:
                        pass
                    if mt == "BUY":
                        n_b += 1
                    elif mt == "SELL":
                        n_s += 1
                    else:
                        n_none += 1
                    r = [x for x in (d.get("refusals") or []) if "no-chase" in x]
                    if r:
                        n_nch += 1
                        derniers.append(
                            (time.strftime("%H:%M:%S", time.gmtime(ts)),
                             d.get("direction"), r[0][:45])
                        )
                elif e in ("shadow_open", "ouverture"):
                    n_open += 1
        lines.append(
            "%s: cand=%d m5[BUY=%d SELL=%d None=%d] nochase=%d OUVERTS=%d"
            % (bot, n_cand, n_b, n_s, n_none, n_nch, n_open)
        )
        for x in derniers[-2:]:
            lines.append("   REFUS %r" % (x,))
        if n_open:
            lines.append("   *** OPEN(S) PRESENT ***")
    with open(LOG, "a", encoding="utf-8") as out:
        out.write("\n".join(lines) + "\n")


def main():
    for _ in range(60):
        try:
            tick()
        except Exception as exc:  # noqa: BLE001 — un tick ne doit jamais tuer le monitor
            with open(LOG, "a", encoding="utf-8") as out:
                out.write("ERR tick: %r\n" % (exc,))
        time.sleep(60)


if __name__ == "__main__":
    main()