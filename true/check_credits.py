import os, httpx
from dotenv import load_dotenv
load_dotenv("/home/redou/QuantLive/.env")
key = os.environ.get("OPENROUTER_API_KEY", "")
r = httpx.get("https://openrouter.ai/api/v1/credits",
              headers={"Authorization": f"Bearer {key}"}, timeout=15).json()
print("RAW:", r)
data = r.get("data", {}) or {}
tc = float(data.get("total_credits") or 0)
uc = float(data.get("used_credits") or 0)
remaining = tc - uc
print(f"\nCrédit restant: ${remaining:.4f}")
# Kimi K3 prix OpenRouter: $0.003 / 1M prompt tokens, $0.015 / 1M completion
price_per_1M = 0.003
prompts_1M = remaining / price_per_1M  # nombre de "1M prompt tokens" possibles
print(f"Equiv prompts de 1M tokens: {prompts_1M:.1f}")
print(f"Equiv prompts de 10k tokens: {prompts_1M * 100:.0f}")
print(f"Equiv prompts de 2k tokens (max actuel): {prompts_1M * 500:.0f}")
