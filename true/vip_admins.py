import sys, time, os
sys.path.insert(0, "/home/redou/QuantLive")
os.chdir("/home/redou/QuantLive")
import app.services.subscription_logic as S

ADMIN_IDS = [6459871864, 1639327628, 8596922561]
DAYS = 3650  # ~10 ans = VIP quasi-permanent

for uid in ADMIN_IDS:
    S.upsert_sub(uid, "", "vip", DAYS, 0, approved_by=6459871864)
    print(f"VIP: {uid}")

print("--- subs actifs ---")
for r in S.list_subs():
    print(r)
