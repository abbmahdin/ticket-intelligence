# CONTINUE: Remise au propre de l'app QuantLive (Mini App UI)

## Contexte
Projet `/home/redou/QuantLive` (FastAPI + PostgreSQL async, WSL, venv `.venv`).
Tu as deja modifie `app/main.py` (ajout router config_app, _notify_maintenance, controleur invisible) — c'est OK, laisse-le tel quel.

## TA MISSION MAINTENANT
Nettoyer `app/api/config_app.py` (2500 lignes, empilement de patches) pour le rendre lisible et fiable SANS casser la Mini App.

### Contraintes CRITIQUES
1. Le bot DOIT continuer de tourner (service `quantlive-bot.service` actif). NE PAS casser l'import de `config_app` dans `main.py`.
2. La sauvegarde (`save()`) via `?k=MINIAPP_SECRET` DOIT continuer de marcher (backend POST ecrit dans .env).
3. La recherche live (`#q`) et le chargement (`load()`) marchent deja — ne les casse pas.
4. La secu: verifier Telegram initData OU `?k=MINIAPP_SECRET`. NE PAS exposer le sJzs6BtqutkVcjzYMo4CfPjBq8MZ3mITIPM9DLvGqhE dans le HTML.

### Bugs connus a corriger
- `config_app.py` a des fonctions JS orphelines (ex: `wireReset` referencee mais sa fonction supprimee) -> encapsule proprement.
- Apostrophes francaises dans template JS qui cassent le parsing -> utilise des guillemets ou echappe.
- Bloc `renderN8nExec` avec `\"` mal echappe.

### Approche
- Lis le fichier COMPLET d'abord (read_file par chunks de 200 lignes).
- Identifie les sections: auth, load, save, render (HTML/JS), wiring events.
- Refactor par petites etapes: une section a la fois, verifie `python -c "import ast; ast.parse(open('app/api/config_app.py').read())"` apres chaque etape.
- NE FAIS PAS de git commit sauf si demande.

### Tests finaux a faire (rapporter)
1. `cd ~/QuantLive && .venv/bin/python -c "from app.api.config_app import router; print('IMPORT OK')"`
2. `curl -s "https://redouan.taile6a245.ts.net/dashboard/config?k=sJzs6BtqutkVcjzYMo4CfPjBq8MZ3mITIPM9DLvGqhE" -o /dev/null -w '%{http_code}'` -> doit donner 200
3. POST test: `curl -s -X POST "https://redouan.taile6a245.ts.net/dashboard/config?k=sJzs6BtqutkVcjzYMo4CfPjBq8MZ3mITIPM9DLvGqhE" -d "ACCOUNT_BALANCE=99999" -o /dev/null -w '%{http_code}'` puis restore `ACCOUNT_BALANCE=100000.0` via le meme endpoint.

### Rapport
Resume en francais ce que tu as nettoye, les fichiers modifies, et confirme que les 3 tests passent.
