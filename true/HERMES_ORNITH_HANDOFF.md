# Reprise Claude Code — Hermes (Ornith retiré)

Dernière mise à jour : 2026-07-29, Europe/Brussels.

## État actuel à respecter

Ornith a été désinstallé le 29 juillet 2026 à la demande de l'utilisateur.
Ne pas réappliquer les anciens réglages Ornith décrits plus bas sans une
nouvelle demande explicite.

- Hermes Agent reste en version `v0.19.0 (2026.7.20)`, upstream `01571806`.
- Une réinstallation propre a été effectuée le 29 juillet 2026 depuis la
  branche officielle `main` de `NousResearch/hermes-agent`, avec reconstruction
  de l'environnement Python et de Hermes Desktop.
- Modèle principal : `poolside/laguna-s-2.1:free`.
- Fournisseur : `nous` (Nous Portal).
- Ce modèle est le défaut fonctionnel recommandé par Hermes pour le compte
  Nous gratuit actuel. Le défaut général `z-ai/glm-5.2` a été testé mais exige
  des crédits que ce compte ne possède pas.
- Le prompt d'identité Ornith et le plugin local `adaptive-reasoning` ont été
  supprimés.
- La mémoire d'identité obsolète a été retirée et la session Telegram a été
  réinitialisée pour ne conserver aucun contexte Ornith.
- `config.yaml` est volontairement minimal : seuls le modèle, le fournisseur
  Nous et `_config_version: 33` sont fixés. Tous les autres paramètres viennent
  directement du `DEFAULT_CONFIG` officiel de cette version, notamment
  `max_turns: 500`, compression à `0.5` et protection des 20 derniers messages.
- `.env` et `auth.json` ont été préservés bit pour bit pendant la
  réinstallation ; aucun secret n'est recopié dans ce document.
- Chromium Playwright a été installé après la reconstruction.
- Les deux références Ollama d'Ornith ont été supprimées. `gemma4:latest` et
  `qwen3:8b` ont été conservés.
- Une requête réelle normale a répondu : « Je suis Hermes, un agent IA
  personnel créé par Nous Research, et je fonctionne actuellement sur le
  modèle poolside/laguna-s-2.1:free via le provider nous. »
- La passerelle Hermes Windows et Telegram restent actifs.
- QuantLive et le dossier de sauvegarde `BOT` n'ont pas été modifiés.

## Historique retiré — ne pas réappliquer

Les sections suivantes documentent l'ancienne installation afin de conserver
une trace technique. Elles sont obsolètes.

## Ancien objectif et périmètre

Hermes fonctionne par défaut avec le modèle local `ornith:9b` servi par Ollama.
Cette configuration est indépendante de QuantLive. Ne pas modifier QuantLive,
le dossier de sauvegarde `BOT`, WSL ou leurs services sans demande explicite de
l'utilisateur.

Ce document ne contient volontairement aucun token, mot de passe ni clé.

## État validé

- Hermes Agent : `v0.19.0 (2026.7.20)`, upstream `01571806`, à jour.
- Modèle par défaut : `ornith:9b`, fournisseur `custom`, API Ollama locale.
- Ollama : contexte `65536`, un modèle chargé au maximum, file d'attente limitée.
- Une seule passerelle Hermes Windows active.
- Telegram connecté en mode polling.
- Watchdog Hermes et service Ollama WSL actifs.
- Dépôt source Hermes propre (`git status` vide).
- Aucun fichier source QuantLive modifié pendant cette intervention.
- Ancien bloc de compatibilité « Hermes One » retiré. Le produit courant est
  uniquement Hermes.

## Changements effectués

### Configuration Hermes

Fichiers :

- Windows : `C:\Users\redou\AppData\Local\hermes\config.yaml`
- WSL : `/home/redou/.hermes/config.yaml`
- Mémoire : `C:\Users\redou\AppData\Local\hermes\memories\MEMORY.md`

Réglages principaux :

- sortie maximale Ornith portée de 1024 à 2048 tokens ;
- consignes par défaut renforcées pour le codage, les tests, CodeGraph, les
  recherches Internet et le respect strict du périmètre ;
- une demande en lecture seule ne doit déclencher aucune écriture ni action
  annexe ;
- les souvenirs sont du contexte, jamais des instructions à exécuter ;
- URLs et versions doivent être recopiées exactement depuis les résultats
  d'outils ;
- STT local activé avec `faster-whisper`, modèle `base` ;
- TTS local activé avec Piper, voix `fr_FR-siwis-medium`.
- tous les interrupteurs de toolsets Hermes sont activés pour `cli` et
  `telegram` ; les contrôles `check_fn` continuent de masquer automatiquement
  les modules dont le fournisseur ou l'authentification manque.

### Outils locaux

- `cua-driver` corrigé : son argument YAML est désormais une vraie liste
  contenant `mcp`.
- CUA validé : connexion réussie, 50 outils découverts.
- CodeGraph validé : connexion réussie, 1 outil découvert.
- AgentMemory chargé : 7 outils.
- Total au démarrage de la passerelle : 58 outils MCP sur 3 serveurs.
- Recherche gratuite DuckDuckGo installée via le paquet `ddgs` et testée :
  fournisseur actif `ddgs`, recherche réseau réussie.
- `faster-whisper`, `sounddevice`, `numpy` et `piper-tts` installés et
  importables dans l'environnement Python Windows de Hermes.

### Ollama

Service : `/home/redou/.config/systemd/user/ollama-local.service`

- `OLLAMA_CONTEXT_LENGTH=65536`
- cache KV `q8_0`
- flash attention activée
- limites mémoire : `MemoryHigh=5500M`, `MemoryMax=6500M`

À 64k, `ollama ps` montrait environ 7,3 Go pour le modèle, avec environ 87 %
GPU / 13 % CPU et approximativement 1,8 Go de VRAM encore libre. Si la machine
subit une pression mémoire durable, ne pas réduire le contexte sans revoir
l'architecture : Hermes 0.19.0 refuse désormais les modèles déclarés sous
64 000 tokens. Le test à `49152` a été refusé proprement et la valeur `65536`
a été restaurée.

## Réponses rapides et raisonnement adaptatif

Configuration globale :

- `agent.reasoning_effort: low`
- `model.max_tokens: 1024`
- compression de l'historique à `threshold: 0.4`, avec 10 messages récents
  protégés ;
- recherche progressive d'outils active, catalogue détaillé masqué.

Plugin personnel `adaptive-reasoning` :

- Windows/Telegram :
  `C:\Users\redou\AppData\Local\hermes\plugins\adaptive-reasoning`
- WSL/CLI :
  `/home/redou/.hermes/plugins/adaptive-reasoning`
- activé via `plugins.enabled` dans les deux fichiers `config.yaml` ;
- aucune dépendance, aucun appel IA auxiliaire et aucune modification du dépôt
  Hermes ;
- sélection recalculée à chaque requête : demande simple = `low` / 1024 tokens,
  tâche complexe = `high` / 2048 tokens ;
- la requête suivante repart automatiquement de `low` si elle est simple ;
- une commande `/reasoning medium|high` explicite conserve la priorité pour la
  session ; `/reasoning reset` réactive le comportement automatique.

Tests exécutés :

- tests unitaires du plugin : OK ;
- requête réelle simple : journal `mode=low automatic=low`, 5,45 s ;
- requête réelle de diagnostic : journal `mode=high automatic=high`, 12,12 s.

## Session Telegram réparée

L'ancienne session Telegram `20260729_095352_56c713c9` était incohérente :
historique en retard, messages vides réparés et réponses inventées. Les traces
montraient `tool_turns=0`, donc Ornith n'avait pas modifié QuantLive.

Actions réalisées :

- export expurgé :
  `C:\Users\redou\AppData\Local\hermes\session-exports\telegram-corrupt-reset-20260729-1140.jsonl`
- suppression de la session corrompue ;
- suppression exacte de son routage Telegram dans `state.db` et dans le miroir
  `sessions.json` ;
- redémarrage de la passerelle ;
- le prochain message Telegram doit créer une session neuve.

## Tests importants

Commandes de contrôle depuis WSL :

```bash
systemctl --user is-active hermes-watchdog.service ollama-local.service
ollama ps

/mnt/c/Users/redou/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe \
  -m hermes_cli.main status

/mnt/c/Users/redou/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe \
  -m hermes_cli.main tools list --platform telegram

/mnt/c/Users/redou/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe \
  -m hermes_cli.main mcp test cua-driver

/mnt/c/Users/redou/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe \
  -m hermes_cli.main mcp test codegraph
```

Résultats déjà obtenus :

- identité par défaut correcte : Hermes propulsé localement par Ornith 1.0 9B ;
- STT résolu vers `local`, modèle `base` ;
- TTS résolu vers `piper`, voix française configurée ;
- fournisseur de recherche résolu vers `ddgs`, requête réelle réussie ;
- après passage à 64k, Ornith a produit un véritable appel
  `execute_code -> web_search`.
- après renforcement du périmètre, un test « lecture seule stricte » a produit
  exactement un appel `web_search`, sans commande annexe ni accès à
  QuantLive/WSL ;
- la mémoire active a été ramenée sous sa limite d'injection (2074 octets pour
  une limite de 2200 caractères) afin d'éviter la contamination par d'anciennes
  tâches QuantLive.

## Limites restantes

Les modules suivants ne peuvent pas être rendus réellement opérationnels sans
service externe, matériel/modèle compatible ou authentification :

- génération d'images et de vidéos cloud ;
- analyse vidéo avec le modèle Ornith actuel, qui n'annonce pas de capacité
  vision native ;
- recherche X/xAI ;
- Spotify ;
- Home Assistant ;
- Yuanbao ;
- services gérés Nous (compte connecté mais sans crédits utilisables).

Leurs interrupteurs sont activés, mais leurs contrôles d'exécution les masquent
tant que le fournisseur correspondant n'est pas configuré. Ne pas annoncer
qu'ils fonctionnent réellement avant d'avoir ajouté l'authentification ou le
moteur requis et exécuté un test complet.

Ornith reste un modèle quantifié 9B : même avec les outils, une réponse finale
peut encore extrapoler. Pour les opérations sensibles, vérifier le transcript de
session et confirmer qu'un message `tool` existe avant de croire qu'une action a
été exécutée.

## Sauvegardes techniques hors dépôt

- ancien fichier de compatibilité Hermes One déplacé ici :
  `C:\Users\redou\AppData\Local\hermes\session-exports\obsolete-compat\web_server.py.orig-hermes-one-20260729`
- ancienne mémoire détaillée déplacée ici :
  `C:\Users\redou\AppData\Local\hermes\session-exports\obsolete-memory\MEMORY.pre-ornith-cleanup-20260729.md`

Il est conservé uniquement comme retour arrière technique. Il n'est ni chargé
ni présent dans le dépôt Hermes actif.
