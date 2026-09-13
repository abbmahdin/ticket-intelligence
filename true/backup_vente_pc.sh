#!/bin/bash
# =============================================================================
# backup_vente_pc.sh — Sauvegarde COMPLETE chiffrée avant vente du PC.
# Crée : /home/redou/QuantLive_backup/vente_pc_<TS>.tar.gz.gpg
#   + dossier déchiffré $DEST (à supprimer ensuite, voir fin du script).
#
# Usage : bash /home/redou/backup_vente_pc.sh
# NE AFFICHE AUCUN SECRET. Passphrase gpg : ~/.quantlive-secrets-backup/.backup_passphrase
# =============================================================================
set -uo pipefail

TS=$(date +%Y%m%d_%H%M)
BASE=/home/redou/QuantLive_backup
DEST=$BASE/vente_pc_${TS}
PASSPHRASE_FILE=/home/redou/.quantlive-secrets-backup/.backup_passphrase
FAIL=0

if [ ! -f "$PASSPHRASE_FILE" ]; then
  echo "ERREUR: passphrase gpg introuvable ($PASSPHRASE_FILE)"; exit 1
fi
if [ ! -f /tmp/.pgbackenv ]; then
  echo "ERREUR: /tmp/.pgbackenv absent — relancer la génération depuis .env"; exit 1
fi

mkdir -p "$DEST"/{db,secrets,systemd,n8n,artifacts,data}
echo "==> Dossier de travail: $DEST"

# ---- 1. Dump Postgres (quantlive + n8n) -----------------------------------
source /tmp/.pgbackenv
echo "==> Dump Postgres: quantlive"
pg_dump -U "$PGUSER" -h "$PGHOST" -p "$PGPORT" -d quantlive -Fc -f "$DEST/db/quantlive.dump" 2>&1 | tail -2
echo "==> Dump Postgres: n8n"
pg_dump -U "$PGUSER" -h "$PGHOST" -p "$PGPORT" -d n8n -Fc -f "$DEST/db/n8n.dump" 2>&1 | tail -2

# Vérif: les dumps doivent exister et être non vides — sinon on ne chiffre RIEN.
for DB in quantlive n8n; do
  if [ ! -s "$DEST/db/$DB.dump" ]; then
    echo "ERREUR: dump $DB absent ou vide — abandon avant chiffrement"; FAIL=1
  fi
done
[ "$FAIL" -eq 1 ] && exit 1
echo "==> Dumps OK ($(du -sh "$DEST"/db/*.dump | awk '{print $1}' | tr '\n' ' '))"

# ---- 2. Secrets & configs ---------------------------------------------------
echo "==> Secrets"
cp /home/redou/QuantLive/.env "$DEST/secrets/.env" 2>/dev/null
cp /home/redou/QuantLive/.env.micro-* "$DEST/secrets/" 2>/dev/null || true
cp /home/redou/QuantLive/mt4_accounts.json "$DEST/secrets/" 2>/dev/null || true
cp /home/redou/.quantlive_options.json "$DEST/secrets/" 2>/dev/null || true
cp /home/redou/.quantlive_presets.json "$DEST/secrets/" 2>/dev/null || true
cp -r /home/redou/.quantlive-secrets-backup "$DEST/secrets/secrets-backup" 2>/dev/null || true
cp -r /home/redou/backupgold_20260904_145940 "$DEST/secrets/backupgold_20260904" 2>/dev/null || true

# ---- 3. Unités systemd user (231) -------------------------------------------
echo "==> Unités systemd user"
tar czf "$DEST/systemd/user-units.tar.gz" -C /home/redou/.config/systemd user 2>/dev/null
echo "==> systemd: $(du -h "$DEST/systemd/user-units.tar.gz" | awk '{print $1}')"

# ---- 4. Export workflows n8n (script versionné, refuse les secrets) ---------
echo "==> Export workflows n8n"
cd /home/redou/QuantLive || exit 1
if [ -f scripts/exporter_workflows_n8n.py ]; then
  .venv/bin/python scripts/exporter_workflows_n8n.py 2>&1 | tail -3
fi
# Copier les exports (le script écrit dans deploy/n8n/workflows)
if [ -d deploy/n8n ]; then
  cp -r deploy/n8n "$DEST/n8n/" 2>/dev/null
  echo "==> n8n exports: $(find "$DEST/n8n" -name '*.json' 2>/dev/null | wc -l) fichiers JSON"
else
  echo "AVERTISSEMENT: deploy/n8n absent — exports n8n non copiés"
fi

# ---- 5. Artefacts (761M, sans caches de modèles .pt lourds) ------------------
echo "==> Artefacts (hors caches .pt)"
tar czf "$DEST/artifacts/artifacts.tar.gz" -C /home/redou/QuantLive artifacts --exclude='*.pt' 2>/dev/null

# ---- 5b. data/ ciblé (runtime, hors hf_cache 15G / third_party 257M régénérables)
echo "==> data/ ciblé (hors hf_cache, third_party, kronos_repo)"
tar czf "$DEST/data/runtime-data.tar.gz" -C /home/redou/QuantLive data \
    --exclude='data/hf_cache' --exclude='data/third_party' --exclude='data/kronos_repo' \
    --exclude='__pycache__' 2>/dev/null

# ---- 6. Archive chiffrée finale --------------------------------------------
echo "==> Archive chiffrée gpg"
cd /home/redou || exit 1
tar czf - -C "$DEST" . 2>/dev/null | \
  gpg --batch --yes --cipher-algo AES256 \
      --passphrase-file "$PASSPHRASE_FILE" \
      -c -o "$BASE/vente_pc_${TS}.tar.gz.gpg"
echo "==> OK: $BASE/vente_pc_${TS}.tar.gz.gpg"

# ---- Vérifications -----------------------------------------------------------
ls -la "$BASE"/vente_pc_${TS}.tar.gz.gpg
echo "==> Vérification chiffrement (symkey enc attendu):"
gpg --list-packets "$BASE"/vente_pc_${TS}.tar.gz.gpg 2>/dev/null | grep -m1 'symkey enc packet' && echo "CHIFFREMENT OK"
echo "==> Vérification déchiffrement (round-trip):"
if gpg --batch --yes --passphrase-file "$PASSPHRASE_FILE" -d "$BASE/vente_pc_${TS}.tar.gz.gpg" 2>/dev/null | tar tzf - > /tmp/.gpg_roundtrip_$TS.txt; then
  echo "DECHIFFREMENT OK — $(wc -l < /tmp/.gpg_roundtrip_$TS.txt) entrées listées"
  rm -f /tmp/.gpg_roundtrip_$TS.txt
else
  echo "ERREUR: le déchiffrement a échoué"; FAIL=1
fi

echo
echo "RECAP:"
du -sh "$DEST"/* 2>/dev/null
du -sh "$BASE"/vente_pc_${TS}.tar.gz.gpg

# ---- Nettoyage ----------------------------------------------------------------
rm -f /tmp/.pgbackenv
echo
echo "NOTE: le dossier déchiffré $DEST contient les secrets en clair."
echo "      Après transfert de l'archive .gpg ailleurs, le supprimer :"
echo "      rm -rf $DEST"
[ "$FAIL" -eq 1 ] && echo "ATTENTION: erreurs détectées (voir plus haut)" && exit 1
echo "BACKUP TERMINE AVEC SUCCES"