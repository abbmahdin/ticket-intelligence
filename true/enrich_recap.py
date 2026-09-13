import re

p = "/home/redou/QuantLive/app/workers/jobs.py"
s = open(p).read()

old = '''async def send_economic_calendar_recap() -> None:
    """[V 2026-07-17] Recap des annonces economiques a venir (FR) -> ORUSDTrade + DM Hermes."""
    from pathlib import Path
    import json
    from datetime import datetime, timezone

    job_id = "send_economic_calendar_recap"
    settings = get_settings()
    if not getattr(settings, "enable_job_economic_recap", False):
        logger.debug("%s: disabled", job_id)
        return
    async with _advisory_lock(job_id) as _locked:
        if not _locked:
            return
        try:
            ev_file = Path(settings.economic_calendar_file)
            if not ev_file.exists():
                logger.info("%s: events.json introuvable", job_id)
                return
            events = json.loads(ev_file.read_text(encoding="utf-8"))
            if not events:
                logger.info("%s: aucun event", job_id)
                return
            now = datetime.now(timezone.utc)
            wanted = {c.strip().upper() for c in settings.economic_calendar_currencies.split(",") if c.strip()}
            def parse_dt(s):
                try:
                    return datetime.fromisoformat(s.replace("Z", "+00:00"))
                except Exception:
                    return None
            upcoming = []
            for ev in events:
                dt = parse_dt(ev.get("starts_at", ""))
                if not dt or dt <= now:
                    continue
                if (ev.get("currency") or "").upper() not in wanted:
                    continue
                if (ev.get("impact") or "").lower() not in ("high", "medium"):
                    continue
                upcoming.append((dt, ev))
            upcoming.sort(key=lambda x: x[0])
            if not upcoming:
                logger.info("%s: aucun event a venir", job_id)
                return
            mois = ["janv.","fevr.","mars","avr.","mai","juin","juil.","aout","sept.","oct.","nov.","dec."]
            jours = ["lun.","mar.","mer.","jeu.","ven.","sam.","dim."]
            def fmt_dt(dt):
                return f"{jours[dt.weekday()]} {dt.day} {mois[dt.month-1]} {dt.hour:02d}:{dt.minute:02d}"
            lines = []
            for dt, ev in upcoming[:12]:
                badge = "ROUGE FORT" if ev.get("impact","").lower()=="high" else "ORANGE MOYEN"
                lines.append(f"{badge} - {ev.get('name','?')} ({ev.get('currency','')}) - {fmt_dt(dt)}")
            recap = ("\\U0001F4C5 EVENEMENTS ECONOMIQUES A VENIR (XAU/USD)\\n"
                     "━━━━━━━━━━━━━━━━━━━━━━━━\\n" + "\\n".join(lines) +
                     "\\n━━━━━━━━━━━━━━━━━━━━━━━━\\n"
                     "⚠️ Le bot penalise la confiance des signaux proches de ces annonces.")
            notifier = _make_notifier(settings)
            await notifier.notify_economic_recap(recap)
            logger.info("%s complete | events=%d", job_id, len(upcoming))
            FailureTracker.record_success(job_id)
        except Exception:
            logger.exception("%s failed", job_id)
            FailureTracker.record_failure(job_id)'''

new = '''async def send_economic_calendar_recap() -> None:
    """[V 2026-07-17] Recap complet des annonces economiques a venir (FR, contexte XAU/USD) -> ORUSDTrade."""
    from pathlib import Path
    import json
    from datetime import datetime, timezone

    job_id = "send_economic_calendar_recap"
    settings = get_settings()
    if not getattr(settings, "enable_job_economic_recap", False):
        logger.debug("%s: disabled", job_id)
        return
    async with _advisory_lock(job_id) as _locked:
        if not _locked:
            return
        try:
            ev_file = Path(settings.economic_calendar_file)
            if not ev_file.exists():
                logger.info("%s: events.json introuvable", job_id)
                return
            events = json.loads(ev_file.read_text(encoding="utf-8"))
            if not events:
                logger.info("%s: aucun event", job_id)
                return
            now = datetime.now(timezone.utc)
            wanted = {c.strip().upper() for c in settings.economic_calendar_currencies.split(",") if c.strip()}
            def parse_dt(s):
                try:
                    return datetime.fromisoformat(s.replace("Z", "+00:00"))
                except Exception:
                    return None
            upcoming = []
            for ev in events:
                dt = parse_dt(ev.get("starts_at", ""))
                if not dt or dt <= now:
                    continue
                if (ev.get("currency") or "").upper() not in wanted:
                    continue
                if (ev.get("impact") or "").lower() not in ("high", "medium"):
                    continue
                upcoming.append((dt, ev))
            upcoming.sort(key=lambda x: x[0])
            if not upcoming:
                logger.info("%s: aucun event a venir", job_id)
                return
            mois = ["janv.","fevr.","mars","avr.","mai","juin","juil.","aout","sept.","oct.","nov.","dec."]
            jours = ["lun.","mar.","mer.","jeu.","ven.","sam.","dim."]
            def fmt_dt(dt):
                return f"{jours[dt.weekday()]} {dt.day} {mois[dt.month-1]} {dt.hour:02d}:{dt.minute:02d}"
            # Contexte par type d'event (FR)
            def contexte(nom):
                n = nom.lower()
                if "fomc" in n or "fed" in n or "rate" in n:
                    return "Decision de taux de la Fed -> fort impact directionnel sur l'or."
                if "cpi" in n or "inflation" in n or "ppi" in n:
                    return "Inflation US -> catalyseur majeur de volatilite sur XAU/USD."
                if "nfp" in n or "payroll" in n or "emploi" in n:
                    return "Emploi US -> relection des anticipations de taux, impact fort."
                if "gdp" in n:
                    return "Croissance US -> sentiment risk-on/off sur l'or."
                if "retail" in n:
                    return "Conso US -> indicateur de sante economique, impact moderne."
                if "jobless" in n or "claims" in n:
                    return "Inscriptions au chomage -> tension sur le dollar, indirect sur l'or."
                return "Event USD a surveiller pour les signaux XAU/USD."
            lines = []
            for dt, ev in upcoming[:12]:
                badge = "ROUGE FORT" if ev.get("impact","").lower()=="high" else "ORANGE MOYEN"
                fc = ev.get("forecast","")
                pv = ev.get("previous","")
                extra = ""
                if fc: extra += f" | Attendu: {fc}"
                if pv: extra += f" | Precedent: {pv}"
                lines.append(
                    f"\\n{badge} - {ev.get('name','?')} ({ev.get('currency','')})\\n"
                    f"   🗓 {fmt_dt(dt)}{extra}\\n"
                    f"   💡 {contexte(ev.get('name',''))}"
                )
            recap = (
                "\\U0001F4C5 EVENEMENTS ECONOMIQUES A VENIR (XAU/USD)\\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━\\n"
                + "\\n".join(lines)
                + "\\n━━━━━━━━━━━━━━━━━━━━━━━━\\n"
                "⚠️ Le bot penalise la confiance des signaux proches de ces annonces."
            )
            notifier = _make_notifier(settings)
            await notifier.notify_economic_recap(recap)
            logger.info("%s complete | events=%d", job_id, len(upcoming))
            FailureTracker.record_success(job_id)
        except Exception:
            logger.exception("%s failed", job_id)
            FailureTracker.record_failure(job_id)'''

assert old in s, "ancien job introuvable"
s = s.replace(old, new, 1)
open(p, "w").write(s)
print("job recap enrichi")
