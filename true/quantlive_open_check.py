import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from app.services.market_hours import is_xauusd_market_open


ROOT = Path('/home/redou/QuantLive')
OUT = ROOT / 'artifacts' / 'market_open_readiness_final.json'
MT5 = Path('/mnt/c/Users/redou/QuantLive_win/mt5_live_status/5000.json')


def get_status():
    with urllib.request.urlopen('http://127.0.0.1:8000/status', timeout=10) as r:
        return json.load(r)


while not is_xauusd_market_open():
    time.sleep(30)

status = get_status()
mt5 = json.loads(MT5.read_text()) if MT5.exists() else {}
result = {
    'checked_at': datetime.now(timezone.utc).isoformat(),
    'market_open': is_xauusd_market_open(),
    'api_status': status.get('status'),
    'database': status.get('database'),
    'scheduler': status.get('scheduler'),
    'watchdog': status.get('watchdog'),
    'telegram': status.get('telegram'),
    'warnings': status.get('warnings'),
    'last_candle_fetch': status.get('last_candle_fetch'),
    'last_signal_generated': status.get('last_signal_generated'),
    'mt5': {
        k: mt5.get(k)
        for k in (
            'connected', 'balance', 'equity', 'kill_switch',
            'trading_blocked', 'total_loss_breached', 'status',
            'positions_count', 'tick', 'ts',
        )
    },
}
OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
print(json.dumps(result, ensure_ascii=False))
