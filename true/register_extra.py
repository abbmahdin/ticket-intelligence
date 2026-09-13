import re

BASE = "/home/redou/QuantLive"

# 1) scheduler.py : import + enregistrement
sched = f"{BASE}/app/workers/scheduler.py"
sc = open(sched).read()

# import
imp_anchor = "from app.workers.jobs import ("
imp_block = (
    "from app.workers.jobs import (\n"
    "    send_economic_calendar_recap,\n"
    ")\n"
    "from app.workers.extra_jobs import (\n"
    "    send_daily_performance_recap,\n"
    "    send_morning_mtf_bias,\n"
    "    check_services_health,\n"
    ")"
)
assert imp_anchor in sc
if "send_daily_performance_recap" not in sc:
    sc = sc.replace(imp_anchor, imp_block, 1)

# enregistrement (apres le bloc economic recap)
recap_anchor = '''    # --- Economic calendar recap (ENABLE_JOB_ECONOMIC_RECAP) ---
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
        logger.info("Job send_economic_calendar_recap disabled (ENABLE_JOB_ECONOMIC_RECAP=false)")'''

new_jobs = recap_anchor + '''

    # --- Daily performance recap (ENABLE_JOB_DAILY_RECAP) ---
    if getattr(settings, "enable_job_daily_recap", False):
        scheduler.add_job(
            send_daily_performance_recap,
            trigger=CronTrigger(hour=22, minute=0, timezone="UTC"),
            id="send_daily_performance_recap",
            name="Daily performance recap (22:00 UTC)",
            replace_existing=True,
        )
        registered += 1
        logger.info("Registered job: send_daily_performance_recap (daily 22:00 UTC)")
    else:
        logger.info("Job send_daily_performance_recap disabled")

    # --- Morning MTF bias (ENABLE_JOB_MTF_BIAS) ---
    if getattr(settings, "enable_job_mtf_bias", False):
        scheduler.add_job(
            send_morning_mtf_bias,
            trigger=CronTrigger(hour=7, minute=5, timezone="UTC"),
            id="send_morning_mtf_bias",
            name="Morning MTF bias (07:05 UTC)",
            replace_existing=True,
        )
        registered += 1
        logger.info("Registered job: send_morning_mtf_bias (daily 07:05 UTC)")
    else:
        logger.info("Job send_morning_mtf_bias disabled")

    # --- Service health check (ENABLE_JOB_SERVICES_HEALTH) ---
    if getattr(settings, "enable_job_services_health", False):
        scheduler.add_job(
            check_services_health,
            trigger=CronTrigger(minute="*/15", timezone="UTC"),
            id="check_services_health",
            name="Service health check (15min)",
            replace_existing=True,
        )
        registered += 1
        logger.info("Registered job: check_services_health (every 15min)")
    else:
        logger.info("Job check_services_health disabled")'''

assert recap_anchor in sc
if "send_daily_performance_recap" not in sc.split("register_jobs")[1]:
    sc = sc.replace(recap_anchor, new_jobs, 1)
open(sched, "w").write(sc)
print("scheduler: 3 jobs enregistres")

# 2) config.py : flags
cfg = f"{BASE}/app/config.py"
c = open(cfg).read()
flags = {
    "enable_job_daily_recap": 'enable_job_daily_recap: bool = Field(default=True, alias="ENABLE_JOB_DAILY_RECAP")',
    "enable_job_mtf_bias": 'enable_job_mtf_bias: bool = Field(default=True, alias="ENABLE_JOB_MTF_BIAS")',
    "enable_job_services_health": 'enable_job_services_health: bool = Field(default=True, alias="ENABLE_JOB_SERVICES_HEALTH")',
}
for key, line in flags.items():
    if key not in c:
        # insere apres enable_job_economic_recap
        anchor = 'enable_job_economic_recap: bool = Field(default=True, alias="ENABLE_JOB_ECONOMIC_RECAP")'
        c = c.replace(anchor, anchor + "\n    " + line)
        print(f"config: {key} ajoute")
    else:
        print(f"config: {key} deja present")
open(cfg, "w").write(c)

# 3) .env
env = f"{BASE}/.env"
e = open(env).read()
for key in ["ENABLE_JOB_DAILY_RECAP", "ENABLE_JOB_MTF_BIAS", "ENABLE_JOB_SERVICES_HEALTH"]:
    if key not in e:
        e = e.rstrip() + f"\n{key}=true\n"
        print(f".env: {key}=true ajoute")
    else:
        print(f".env: {key} deja present")
open(env, "w").write(e)

print("DONE")
