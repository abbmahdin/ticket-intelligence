# Inventaire des Projets — /home/redou/

**Date** : 2026-09-13

---

## 1. QuantLive

| Attribut | Valeur |
|---|---|
| **Chemin** | `/home/redou/QuantLive/` |
| **Remote** | `github.com:abbmahdin/QuantLive` |
| **Branche** | `feat/micro-trades-noyau-shadow` |
| **Fichiers** | ~81 000 (10 000 dossiers) |
| **Dernier commit** | `d148f63 feat(micro): sens de tendance = pente EMA50 H4 (MICRO_SENS_H4)` |

**État Git** : **TRÈS ACTIF** — 31 fichiers modifiés, 1 untracked (`FLIP_PROTECTIVE_NOTES.md`) :
- Config : `MODIFS.md`, `app/config.py`, `app/micro/config.py`
- Micro-trades : `app/micro/gates.py`, `app/micro/loop.py`, `app/micro/regime.py`
- Artifacts : une vingtaine de fichiers JSON (agent_code, cross_corr, dashboard, geo_pol, info, signal_multisource, symbiose, trend_*)
- Scripts : `surveillant_positions.py`
- Tests : `tests/micro/test_loop.py`, `tests/unit/test_surveillant_positions.py`

**Tests** : Fichiers `tests/` présents mais non exécutés ici (besoin DB PostgreSQL).

**Documentation** : `README.md` + `.planning/` (7 phases, STATE.md, PROJECT.md, CHECKLIST).

**TODO/FIXME** :
- `mt4_ea/QuantLiveBridge.mq4` (patterns `else if` — code MQL4)
- `scripts/m9m_code_agent.py` : compte automatiquement TODO/FIXME/HACK
- `.planning/STATE.md` : Phase 7 en cours (1/2 plans), 96% complété, 07-01 encore ouvert (Railway deployment)

**Ce qui reste** :
- ⚠️ Finaliser le déploiement Railway (07-01-PLAN.md) : configurer PostgreSQL plugin, GitHub auto-deploy, env vars
- ⚠️ Commit & push des 31 fichiers modifiés
- ⚠️ Résoudre les TODO dans `quantlive_mcp/tools/` (backtest, signal, audit non connectés au vrai moteur)
- ⚠️ Vider les 70+ backups `.env.bak_*`

---

## 2. quantlive-mcp

| Attribut | Valeur |
|---|---|
| **Chemin** | `/home/redou/quantlive-mcp/` |
| **Remote** | `github.com:abbmahdin/quantlive-mcp` |
| **Branche** | `master` |
| **Fichiers source** | ~50 (Dockerfile, fly.toml, server.py, tools/, tests/) |
| **Dernier commit** | `cb965a5 chore: add Dockerfile and fly.toml (health check on /health)` |

**État Git** : ✅ CLEAN

**Tests** : ✅ **55 passed, 1 warning** (pytest, 3.15s) :
- `test_server.py` (10 tests : FastAPI, Stripe webhooks, error handling)
- `test_reconcile.py` + `test_reconcile_cli.py` (réconciliation)
- `test_skill_pack.py` (4 skill manifests)
- `test_x402_middleware.py` (12 tests : paiements USDC onchain)

**Documentation** : `README.md`, `Dockerfile`, `fly.toml`

**TODO** :
- `tools/backtest.py:30` — `# TODO: Connect to actual QuantLive backtest engine`
- `tools/signal.py:30` — `# TODO: Connect to actual QuantLive signal generation`
- `tools/audit.py:22` — `# TODO: Connect to actual QuantLive position monitor`

**Ce qui reste** :
- ⚠️ Connecter les 3 outils au vrai moteur QuantLive (actuellement stubs)
- ⚠️ Déployer sur Fly.io (Dockerfile + fly.toml présents mais jamais déployés)

---

## 3. Desktop/BOT

| Attribut | Valeur |
|---|---|
| **Chemin** | `/home/redou/Desktop/BOT/` |
| **Remote** | Aucun (local only) |
| **Branche** | `master` |
| **Fichiers** | ~26 (MT4/QuantLiveBridge.mq4, systemd/, QuantLive/) |
| **Dernier commit** | `3911ad5 chore: synchro slots 10/10` |

**État Git** : 30+ fichiers supprimés (`QuantLive/.agents/skills/`), `MT4/QuantLiveBridge.mq4` modifié.

**Documentation** : `README.md`

**Ce qui reste** :
- ⚠️ 30+ fichiers de skills supprimés (agentmemory-*, commit-context, etc.) — à commit ou restaurer
- ⚠️ Pas de remote configuré
- ⚠️ `QuantLive/.claude/skills/agentmemory-*` supprimés (trailing slash dans git status)

---

## 4. gotfhater-bot

| Attribut | Valeur |
|---|---|
| **Chemin** | `/home/redou/gotfhater-bot/` |
| **Remote** | `github.com:abbmahdin/gotfhater-bot` |
| **Branche** | `master` |
| **Fichiers source** | ~30 (bot.py, miniapp.py, health_server.py, security.py, watchdog.py, systemd/) |
| **Dernier commit** | `306e67d Mini-app: cards FVG (SMC), Killzone ICT, Portfolio Heat` |

**État Git** : `bot.py` modifié (non commité).

**Tests** : `_test_miniapp.py`, `_test_security.py`, `watchdog/_test_watchdog.py`, `watchdog/_test_stripe_probe.py` — non exécutés ici (serveur requis).

**Documentation** : `README.md`, `watchdog/README.md`, `install_user_service.sh`

**Services** : systemd units pour bot, miniapp, health, watchdog (timer), tunnel.

**Ce qui reste** :
- ⚠️ Commit & push `bot.py` modifié
- ⚠️ Watchdog `_test_watchdog.py` : cron job Stripe probe (cron installé ?)
- ⚠️ Tests unitaires à exécuter

---

## 5. ecc-review

| Attribut | Valeur |
|---|---|
| **Chemin** | `/home/redou/ecc-review/` |
| **Remote** | `github.com:affaan-m/ecc.git` |
| **Branche** | `main` |
| **Dernier commit** | `5064474 fix: integrate verified ECC 2.2.1 maintenance patches (#3012)` |

**État Git** : `selection/` untracked.

**Documentation** : Très complète — `README.md`, `README.zh-CN.md`, `CHANGELOG.md`, `RULES.md`, `SECURITY.md`, `CONTRIBUTING.md`, `CLAUDE.md`, `SOUL.md`, `WORKING-CONTEXT.md`, `COMMANDS-QUICK-REF.md`, `TROUBLESHOOTING.md`, `the-longform-guide.md`, `the-security-guide.md`, `the-shortform-guide.md`.

**Ce qui reste** :
- ⚠️ `selection/` : dossier non suivi (?) — vérifier et commit ou ajouter à .gitignore

---

## 6. monbot

| Attribut | Valeur |
|---|---|
| **Chemin** | `/home/redou/monbot/` |
| **Remote** | `github.com:abbmahdin/monbot` |
| **Branche** | `master` |
| **Fichiers source** | ~30 (bot.py, miniapp.py, diag_*.py, js_guard.py, veille_state.py, 13 fichiers de test) |
| **Dernier commit** | `0152518 fix(heartbeat): ignorer comptes MT4 desarmes (ftmo-1) + retirer concordia-bridge/bot-principal de la diag` |

**État Git** : ✅ CLEAN

**Tests** : ✅ `_test_diag_n8n.py` — 15 tests OK (exécutés avec succès). 12 autres fichiers de test disponibles (`_test_diag_quota.py`, `_test_presets.py`, `_test_repair.py`, `_test_pnl.py`, `_test_pwa.py`, `_test_status_job.py`, etc.) + `run_all_tests.sh`.

**Documentation** : `README.md`, `portable/INSTALLER.bat`, `portable/install_windows.ps1`

**Ce qui reste** :
- ⚠️ `_test_miniapp.py` : nécessite serveur live sur port 8003 (monbot-miniapp.service)
- ⚠️ `_test_diag_mt4_guards.py` : nécessite connexion MT4
- ⚠️ `portable/` : scripts d'installation Windows (à tester/maintenir)

---

## 7. quantlive-desktop

| Attribut | Valeur |
|---|---|
| **Chemin** | `/home/redou/quantlive-desktop/` |
| **Remote** | `github.com:abbmahdin/quantlive-desktop` |
| **Branche** | `master` |
| **Fichiers** | ~16 000 (incluant node_modules/) |
| **Dernier commit** | `3207bba chore(bundle): jeu d icones Tauri complet + tauri.conf.json icon list` |

**État Git** : ✅ CLEAN

**Technologie** : Tauri + frontend JS (vitest.config.js, app.test.js, @tauri-apps/api).

**Tests** : `src/app.test.js` + `vitest.config.js` — non exécutés ici.

**Documentation** : `README.md`

**Ce qui reste** :
- ⚠️ Les TODO dans node_modules sont externes (normal)
- ⚠️ Exécuter `npm test` / `vitest` pour vérifier les tests internes

---

## 8. qcontrol

| Attribut | Valeur |
|---|---|
| **Chemin** | `/home/redou/qcontrol/` |
| **Remote** | Aucun (local only) |
| **Branche** | `master` |
| **Fichiers source** | 4 (app.py ~24KB, index.html ~28KB, send_miniapp_button.py) |
| **Dernier commit** | `50011f8 fix(ui): raccourcis zoom ne perturbent plus la frappe dans les champs (isEditing guard)` |

**État Git** : ✅ CLEAN

**Documentation** : ⚠️ Pas de README

**Tests** : ⚠️ Aucun test

**Ce qui reste** :
- ⚠️ Pas de README (ajouter documentation)
- ⚠️ Pas de remote configuré (sauvegarde locale uniquement)
- ⚠️ Pas de tests
- ⚠️ `__pycache__` non ignoré dans .gitignore

---

## 9. .openclaw/workspace

| Attribut | Valeur |
|---|---|
| **Chemin** | `/home/redou/.openclaw/workspace/` |
| **Remote** | Aucun |
| **Branche** | `master` (aucun commit) |
| **Fichiers** | ~29 (AGENTS.md, DREAMS.md, IDENTITY.md, SOUL.md, USER.md, memory/) |

**État Git** : 7 fichiers untracked (`.serena/`, `AGENTS.md`, `DREAMS.md`, `IDENTITY.md`, `SOUL.md`, `USER.md`, `memory/`) — aucun commit effectué.

**Documentation** : AGENTS.md (8KB), SOUL.md (2KB), USER.md, IDENTITY.md, DREAMS.md

**Ce qui reste** :
- ⚠️ Initialiser le premier commit
- ⚠️ Configurer un remote
- ⚠️ Activer le suivi de `memory/` (carnets de rêves, notes de veille)

---

## 10. saas-mvp

**N'existe pas encore.** Référence dans `.openclaw/workspace/memory/` comme projet en cours d'étude (recherche micro-SaaS/data/template avec revenus vérifiés).

---

## Résumé des priorités

| Priorité | Projet | Action |
|---|---|---|
| 🔴 HAUT | QuantLive | Commit/push 31 fichiers, finaliser Railway (Phase 7) |
| 🔴 HAUT | Desktop/BOT | 30+ fichiers supprimés (skills), à commit ou restaurer |
| 🔴 HAUT | gotfhater-bot | Commit/push `bot.py` modifié |
| 🟡 MOYEN | quantlive-mcp | Connecter outils au vrai moteur, déployer Fly.io |
| 🟡 MOYEN | qcontrol | Ajouter README, remote, tests |
| 🟡 MOYEN | .openclaw/workspace | Initialiser commit, configurer remote |
| 🟢 BAS | ecc-review | Commit `selection/` |
| 🟢 BAS | monbot | Véririfier `_test_miniapp` (serveur 8003), MT4 guards |
| 🟢 BAS | quantlive-desktop | Exécuter `npm test` |
| 🟢 BAS | saas-mvp | Créer le dossier / initialiser le projet |