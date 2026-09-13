import subprocess, os, re

# 1) Unites systemd n8n
print("=== Unites systemd n8n ===")
out = subprocess.run(["systemctl", "--user", "list-units", "--no-pager"], capture_output=True, text=True).stdout
for line in out.splitlines():
    if "n8n" in line.lower():
        print(" ", line[:120])

# 2) Contenu des fichiers service n8n (Environment=)
print()
print("=== Fichiers service n8n (lignes Environment) ===")
for f in ["~/.config/systemd/user/n8n.service", "~/.config/systemd/user/n8n-calendar.service"]:
    path = os.path.expanduser(f)
    if os.path.exists(path):
        print(f"--- {f} ---")
        for line in open(path):
            if "Environment" in line:
                print("  ", line.strip()[:160])

# 3) Essai: /proc des pids n8n
print()
print("=== Env via /proc (pids n8n) ===")
out = subprocess.run(["pgrep", "-f", "n8n"], capture_output=True, text=True).stdout.strip()
pids = out.split()
seen = set()
for pid in pids:
    try:
        with open(f"/proc/{pid}/environ") as fh:
            env = fh.read().split("\0")
        for e in env:
            if any(x in e for x in ("TELEGRAM_CHAT_ID", "TWELVE_DATA", "ECON_CALENDAR", "GSHEET_ID", "SOURCE_HEARTBEAT", "N8N_")):
                k, _, v = e.partition("=")
                if (k, pid) not in seen:
                    seen.add((k, pid))
                    print(f"  pid {pid}: {k}={v[:60]}")
    except Exception:
        pass
