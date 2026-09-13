import re

BASE = "/home/redou/QuantLive"

# 1) Ajouter notify_economic_recap au notifier (apres notify_health_digest)
notif = f"{BASE}/app/services/telegram_notifier.py"
s = open(notif).read()
anchor = '''    async def notify_health_digest(self, stats: dict) -> bool:
        if not self._non_signal_allowed("health_digest"):
            return False

        decision = self._guard.check(production_alert=True)
        if not decision.allowed:
            logger.debug("Telegram health digest blocked [{}]", decision.reason)
            return False
        try:
            text = self.format_health_digest(stats)
            await self._send_message(text)
            logger.info("Telegram health digest sent")
            return True
        except Exception:
            logger.exception("Telegram health digest failed")
            return False
'''
add = anchor + '''
    async def notify_economic_recap(self, text: str) -> bool:
        """[V 2026-07-17] Envoie le recap des annonces economiques (francais)."""
        if not self._non_signal_allowed("economic_recap"):
            return False
        decision = self._guard.check(production_alert=True)
        if not decision.allowed:
            logger.debug("Telegram economic recap blocked [{}]", decision.reason)
            return False
        try:
            await self._send_message(text)
            logger.info("Telegram economic recap sent")
            return True
        except Exception:
            logger.exception("Telegram economic recap failed")
            return False
'''
assert anchor in s, "anchor notif introuvable"
s = s.replace(anchor, add, 1)
open(notif, "w").write(s)
print("notifier: notify_economic_recap ajoute")

# 2) Ajouter le job send_economic_calendar_recap dans jobs.py (apres send_health_digest complet)
jobs = f"{BASE}/app/workers/jobs.py"
j = open(jobs).read()

# trouve la fin de send_health_digest (le bloc except final + retour a la ligne)
end_anchor = '''                await notifier.notify_system_alert(
                    "Health Digest Failing",
                    f"Health digest job has failed {count} consecutive times\\n\\n"
                    f"<b>Error:</b> {err_type}",
                )


async def run_param_optimization() -> None:'''
job_code = '''                await notifier.notify_system_alert(
                    "Health Digest Failing",
                    f"Health digest job has failed {count} consecutive times\\n\\n"
                    f"<b>Error:</b> {err_type}",
                )


async def send_economic_calendar_recap() -> None:
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
            # DM Hermes si configure
            ht = getattr(settings, "hermes_bot_token", "") or ""
            hc = getattr(settings, "hermes_dm_chat_id", "") or ""
            if ht and hc:
                try:
                    import httpx
                    async with httpx.AsyncClient(timeout=15) as client:
                        await client.post(f"https://api.telegram.org/bot{ht}/sendMessage",
                                          json={"chat_id": hc, "text": recap, "parse_mode": "HTML"})
                except Exception as e:
                    logger.warning("%s: DM Hermes echec: %s", job_id, e)
            logger.info("%s complete | events=%d", job_id, len(upcoming))
            FailureTracker.record_success(job_id)
        except Exception:
            logger.exception("%s failed", job_id)
            FailureTracker.record_failure(job_id)


async def run_param_optimization() -> None:'''

assert end_anchor in j, "anchor jobs introuvable"
j = j.replace(end_anchor, job_code, 1)
open(jobs, "w").write(j)
print("jobs: send_economic_calendar_recap ajoute")

# 3) Enregistrer dans scheduler.py
sched = f"{BASE}/app/workers/scheduler.py"
sc = open(sched).read()
# ajout apres le bloc health digest
hd_anchor = '''    # --- Health digest (ENABLE_JOB_HEALTH_DIGEST) ---'''
recap_reg = '''    # --- Economic calendar recap (ENABLE_JOB_ECONOMIC_RECAP) ---
    if getattr(settings, "enable_job_economic_recap", False):
        scheduler.add_job(
            send_economic_calendar_recap,
            trigger=CronTrigger(hour=7, minute=0, timezone="UTC"),
            id="send_economic_calendar_recap",
            name="Economic calendar recap (daily 07:00 UTC)",
            replace_existing=True,
        )
        registered += 1
        logger.info("Registered job: send_economic_calendar_recap (daily 07:00 UTC)")
    else:
        logger.info("Job send_economic_calendar_recap disabled (ENABLE_JOB_ECONOMIC_RECAP=false)")

    # --- Health digest (ENABLE_JOB_HEALTH_DIGEST) ---'''
assert hd_anchor in sc, "anchor scheduler introuvable"
sc = sc.replace(hd_anchor, recap_reg, 1)
# import du job
if "send_economic_calendar_recap" not in sc.split("register_jobs")[0]:
    # ajoute dans les imports en haut
    imp_anchor = "from app.workers.jobs import ("
    imp_block = '''from app.workers.jobs import (
    send_economic_calendar_recap,'''
    # on insere juste apres la premiere ligne d'import si presente, sinon on ajoute
    if imp_anchor in sc:
        sc = sc.replace(imp_anchor, imp_block, 1)
    else:
        sc = "from app.workers.jobs import send_economic_calendar_recap\n" + sc
open(sched, "w").write(sc)
print("scheduler: job enregistre")

# 4) Config flag
cfg = f"{BASE}/app/config.py"
c = open(cfg).read()
if "enable_job_economic_recap" not in c:
    # insere apres enable_job_health_digest
    hd = 'enable_job_health_digest: bool = Field(default=True, alias="ENABLE_JOB_HEALTH_DIGEST")'
    c = c.replace(hd, hd + '\n    enable_job_economic_recap: bool = Field(default=True, alias="ENABLE_JOB_ECONOMIC_RECAP")')
    open(cfg, "w").write(c)
    print("config: enable_job_economic_recap ajoute")
else:
    print("config: deja present")

# 5) .env
env = f"{BASE}/.env"
e = open(env).read()
if "ENABLE_JOB_ECONOMIC_RECAP" not in e:
    e = e.rstrip() + "\nENABLE_JOB_ECONOMIC_RECAP=true\n"
    open(env, "w").write(e)
    print(".env: ENABLE_JOB_ECONOMIC_RECAP=true ajoute")
else:
    print(".env: deja present")

print("ALL DONE")
