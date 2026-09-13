# TACHE: Extraire transcriptions des videos cles + ameliorer les strategies LIT

Dossier: /mnt/c/Users/redou/OneDrive/Bureau/V (videos formation trading, MP4)

## Objectif
1. Installer les outils manquants: ffmpeg + openai-whisper (dans le venv .venv du projet `~/QuantLive`).
   - ffmpeg: apt-get install -y ffmpeg (ou telechargement static)
   - openai-whisper: pip install openai-whisper (dans .venv)
2. Extraire l'audio (WAV 16kHz mono) de CES 2 videos:
   - "11.2 Momentum Mitigation.MP4"   (181 MB, correspond a la strategie momentum_mitigation du bot)
   - "5 Inducement Basic Rulesets.MP4" (75 MB, pour lit_inducement / big4_inducements)
   Utilise ffmpeg: ffmpeg -i IN.mp4 -ar 16000 -ac 1 OUT.wav
3. Transcrire avec whisper (modele "base" ou "small" si dispo, sinon "tiny" pour rapidite):
   whisper OUT.wav --model base --language en --output_format txt
4. Pour CHAQUE video, analyser la transcription et en tirer les REGLES EXPLICITES de trading
   (conditions d'entree, structure, invalidation, timeframe) traduisibles en code Python.
5. Comparer avec l'implementation actuelle du bot:
   - momentum_mitigation: app/strategies/momentum_mitigation.py
   - lit_inducement: app/strategies/lit_inducement.py + app/services/lit_mtf_context.py
   - big4_inducements: app/strategies/big4_inducements.py
   Et proposer des PATCHS concrets (en francais, avec le code) pour aligner le bot sur la methode de la video.

## Contraintes
- NE PAS modifier les strategies pour l'instant — juste produire un RAPPORT avec:
  (a) la transcription extraite (ou resume fidele si tres long)
  (b) les regles de trading identifiees
  (c) les ecarts avec le code actuel
  (d) les patchs proposes (code Python) pour chaque strategie
- Utilise le dossier /tmp pour les fichiers intermediaires (wav/txt) — pas besoin de les garder.
- Rapporte en francais, concisement.

## Note
Les videos sont sur le disque Windows monte en /mnt/c. Le projet est ~/QuantLive (WSL).
Le bot tourne deja (service actif) — ne pas le redemarrer sauf si un patch est explicitement applique (pas le cas ici, rapport seulement).
