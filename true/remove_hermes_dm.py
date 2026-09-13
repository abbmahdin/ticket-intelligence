p = "/home/redou/QuantLive/app/workers/jobs.py"
s = open(p).read()
block = (
    '            notifier = _make_notifier(settings)\n'
    '            await notifier.notify_economic_recap(recap)\n'
    '            # DM Hermes si configure\n'
    '            ht = getattr(settings, "hermes_bot_token", "") or ""\n'
    '            hc = getattr(settings, "hermes_dm_chat_id", "") or ""\n'
    '            if ht and hc:\n'
    '                try:\n'
    '                    import httpx\n'
    '                    async with httpx.AsyncClient(timeout=15) as client:\n'
    '                        await client.post(f"https://api.telegram.org/bot{ht}/sendMessage",\n'
    '                                          json={"chat_id": hc, "text": recap, "parse_mode": "HTML"})\n'
    '                except Exception as e:\n'
    '                    logger.warning("%s: DM Hermes echec: %s", job_id, e)\n'
    '            logger.info("%s complete | events=%d", job_id, len(upcoming))'
)
repl = (
    '            notifier = _make_notifier(settings)\n'
    '            await notifier.notify_economic_recap(recap)\n'
    '            logger.info("%s complete | events=%d", job_id, len(upcoming))'
)
assert block in s, "bloc DM Hermes introuvable"
s = s.replace(block, repl, 1)
open(p, "w").write(s)
print("DM Hermes retire du job")
