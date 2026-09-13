# Mission : Vérifier, corriger et compléter les 3 features QuantLive

## Contexte

J'ai implémenté 3 features dans `/home/redou/QuantLive/` :
1. **Dashboard trades temps réel** — API REST `/api/trades/live` + WebSocket `/api/trades/ws`
2. **Alertes Telegram enrichies** — caption builder enrichi (déjà existant, tests ajoutés)
3. **Backtesteur unifié** — API async `/api/backtest/run|status|result|strategies`

Tu es un reviewer senior. Voici ta mission en 3 phases.

---

## Phase 1 — VÉRIFICATION (lis TOUS les fichiers listés)

Lis ces 9 fichiers et note TOUT bug, toute incohérence, et toute chose manquante :

```
QuantLive/app/schemas/trades.py
QuantLive/app/schemas/backtest.py
QuantLive/app/api/trades_live.py
QuantLive/app/api/backtest.py
QuantLive/app/services/backtest_service.py
QuantLive/app/main.py
QuantLive/tests/test_trades_live.py
QuantLive/tests/test_backtest_api.py
QuantLive/tests/test_telegram_enriched.py
```

Cherche spécifiquement :

### Bugs probables (liste non exhaustive — trouve TOUT) :

1. **Pydantic `utcnow` déprécié** : `app/schemas/trades.py` utilise `Field(default_factory=datetime.utcnow)` sur `LiveTradesResponse.last_updated` et `TradeEvent.timestamp` → Pydantic v2 émet un DeprecationWarning.À remplacer par `datetime.now(timezone.utc)`.

2. **Test `test_enriched_caption` qui va échouer** : `tests/test_telegram_enriched.py:42` vérifie `"Config" in caption` mais le caption builder produit `CONFIGURATION` (majuscules). La recherche est case-sensitive → `"Config" in "CONFIGURATION"` est False.

3. **Test backtest qui dépend de la registry réelle** : `tests/test_backtest_api.py:test_run_valid` patche `enqueue_backtest` mais PAS `BaseStrategy.get_registry()`. Si `stoch_trend` n'est pas dans la registry réelle au moment du test, le router lève HTTPException(400) AVANT d'appeler `enqueue_backtest` → le mock ne sert à rien, le test retourne 400 au lieu de 200.

4. **Race condition dans backtest_service.py** : `_run_backtest()` lit `task` sous le lock, puis le mute (`status="running"`, `started_at=...`) HORS lock. Un appel concurrent à `get_task_status()` peut voir un état partiellement écrit (ex: `status="running"` mais `started_at=None`).

5. **Chemin relatif fragile** : `_TRADES_VUS_FILE = Path("QuantLive/data/trades_ouverts_vus.json")` dans `trades_live.py`. Si le process uvicorn est lancé depuis un autre répertoire, le fichier ne sera pas trouvé → les données MT4 sont silencieusement absentes.

6. **`_build_trades` avale toutes les exceptions** : Le `except Exception: logger.exception(...)` sans `raise` fait que la liste est vide sans erreur visible pour l'appelant → l'API retourne 200 avec `trades: []` même si la DB est down.

7. **Import non vérifié** : `app/services/backtest_service.py` importe `from app.services.metrics_calculator import BacktestMetrics` et `from app.strategies.base import BaseStrategy`. Vérifie que ces modules existent réellement et que `BacktestMetrics` a bien les attributs `win_rate`, `profit_factor`, `sharpe_ratio`, `max_drawdown`, `total_trades`, `total_wins`, `total_losses`, `expectancy`, `avg_rr`.

### Choses manquantes à trouver :

8. **Pas d'authentification sur les nouvelles routes** : Les routes existantes (dashboard, admin, etc.) utilisent `Depends(verify_...)` ou des middlewares. Les nouvelles routes `/api/trades/*` et `/api/backtest/*` n'ont aucune protection. Cherche comment les autres routes sont protégées et applique le même pattern.

9. **Pas de config dans `app/config.py`** : Les nouvelles features n'ont aucune entrée de configuration (feature flags, TTL des tâches backtest, etc.). Ajoute `backtest_task_ttl_seconds: int = 1800` et `trades_live_enabled: bool = True` dans `Settings`.

10. **Pas de rate limiting sur le backtest** : N'importe qui peut lancer 1000 backtests en parallèle et saturer le CPU. Ajoute une limite (ex: max 3 tâches concurrentes, queue FIFO).

11. **WebSocket incomplet** : Le WebSocket actuel ne fait que du polling (sleep 5s). Il n'y a aucun mécanisme de broadcast quand un trade est créé/modifié. Il faut soit un pub/sub (Redis), soit un mécanisme interne de callback.

12. **Symboles hardcodés** : `symbol="XAUUSD"` est hardcodé dans `_build_trades` et `_read_mt4_statuses`. Devrait être configurable ou déduit des données.

13. **Pas de `__init__.py` ou d'exports** : Vérifie si `app/api/__init__.py` et `app/services/__init__.py` existent et s'ils doivent exporter les nouveaux modules.

14. **Pas de migration DB pour le backtest** : Si le backtest doit persister ses résultats en DB, il faut une table. Sinon, c'est acceptable (in-memory).

15. **`datetime.utcnow` aussi dans `trades_live.py:109`** : Le endpoint `trades_live` utilise `datetime.now(timezone.utc)` (OK) mais vérifie qu'il n'y a pas d'autres `utcnow()` dans les nouveaux fichiers.

---

## Phase 2 — CORRECTION

Pour chaque bug trouvé, applique la correction minimale. Priorité :

1. **Critiques** (cassent les tests ou la prod) → corrige d'abord
2. **Moyens** (race, sécurité, config manquante) → corrige ensuite
3. **Cosmétiques** (warnings, noms) → corrige en dernier

Règles :
- Modifie le moins de code possible
- Utilise les patterns existants du codebase (ex: `Depends(get_session)`, `HTTPException`, `logger.exception`)
- Après chaque correction, relance `cd /home/redou/QuantLive && .venv/bin/pytest tests/test_trades_live.py tests/test_telegram_enriched.py tests/test_backtest_api.py -v --tb=short` et vérifie que les tests passent

---

## Phase 3 — COMPLÉTION

Après avoir corrigé les bugs, ajoute ce qui manque pour que les features soient "production-ready" :

1. **Auth sur les nouvelles routes** — même pattern que les autres routes
2. **Config dans app/config.py** — feature flags + TTL
3. **Rate limiting backtest** — max 3 concurrents
4. **Chemin `_TRADES_VUS_FILE`** — utilise un chemin absolu basé sur `app.config` ou `Path(__file__).parent.parent.parent`
5. **Gestion d'erreur dans `_build_trades`** — distingue "DB down" (500) de "aucun trade" (200 vide)

---

## Contrainte finale

À la fin, TOUS les tests doivent passer :
```
.venv/bin/pytest tests/test_trades_live.py tests/test_telegram_enriched.py tests/test_backtest_api.py -v
```

Fais un résumé de chaque bug trouvé, chaque correction appliquée, et chaque ajout fait.