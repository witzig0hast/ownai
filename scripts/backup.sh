#!/usr/bin/env bash
# Sichert alles, was OwnAI ausmacht, in ein Verzeichnis pro Lauf:
#   db.dump        - komplette Postgres-Datenbank (pg_dump, custom format)
#   files.tar.gz   - vom Assistenten erzeugte Dateien (Volume backend_files)
#   env.backup     - Kopie der .env (enthält SECRET_KEY - ohne den lassen sich gespeicherte
#                    Zugangsdaten wie CalDAV/Home-Assistant/SMTP nach einem Restore nicht mehr
#                    entschlüsseln!)
#
# Aufruf (aus dem Repo-Verzeichnis oder von überall):
#   scripts/backup.sh                 -> ./backups/<zeitstempel>/
#   scripts/backup.sh /mnt/nas/ownai  -> /mnt/nas/ownai/<zeitstempel>/
# BACKUP_KEEP=14 (Standard) behält die 14 neuesten Sicherungen im Zielverzeichnis, ältere werden
# gelöscht. BACKUP_KEEP=0 löscht nie.
#
# Als täglicher Cronjob (3:15 Uhr), z.B. per `crontab -e`:
#   15 3 * * * /pfad/zu/ownai/scripts/backup.sh /mnt/nas/ownai >> /var/log/ownai-backup.log 2>&1
set -euo pipefail
umask 077

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

TARGET_ROOT="${1:-$REPO_DIR/backups}"
KEEP="${BACKUP_KEEP:-14}"

if [[ ! -f .env ]]; then
  echo "Fehler: keine .env in $REPO_DIR gefunden." >&2
  exit 1
fi

# Nur die zwei Werte lesen, die wir brauchen, statt die ganze .env zu sourcen (die ist kein
# Shell-Skript und kann Werte mit Leer-/Sonderzeichen enthalten).
env_value() {
  grep -E "^$1=" .env | tail -n1 | cut -d= -f2- | sed -e 's/^"//' -e 's/"$//'
}
PG_USER="$(env_value POSTGRES_USER)"
PG_DB="$(env_value POSTGRES_DB)"
: "${PG_USER:?POSTGRES_USER fehlt in .env}"
: "${PG_DB:?POSTGRES_DB fehlt in .env}"

STAMP="$(date +%Y-%m-%d_%H%M%S)"
DEST="$TARGET_ROOT/$STAMP"
mkdir -p "$DEST"
echo "==> Sichere nach $DEST"

echo "--> Datenbank"
docker compose exec -T postgres pg_dump -U "$PG_USER" -d "$PG_DB" --format=custom > "$DEST/db.dump.partial"
mv "$DEST/db.dump.partial" "$DEST/db.dump"

echo "--> Erzeugte Dateien"
if docker compose ps --status running --services | grep -qx backend; then
  docker compose exec -T backend sh -c 'mkdir -p /app/data/files && tar -C /app/data -czf - files' \
    > "$DEST/files.tar.gz"
else
  docker compose run --rm --no-deps -T backend sh -c 'mkdir -p /app/data/files && tar -C /app/data -czf - files' \
    > "$DEST/files.tar.gz"
fi

echo "--> .env"
cp .env "$DEST/env.backup"

# Ein abgebrochener Lauf hinterlässt kein Verzeichnis, das wie eine vollständige Sicherung aussieht.
touch "$DEST/COMPLETE"

if [[ "$KEEP" -gt 0 ]]; then
  # Verzeichnisnamen sind Zeitstempel, sortieren also chronologisch. Nur vollständige Sicherungen
  # zählen und werden aufgeräumt.
  mapfile -t complete < <(find "$TARGET_ROOT" -mindepth 2 -maxdepth 2 -name COMPLETE -printf '%h\n' | sort)
  excess=$(( ${#complete[@]} - KEEP ))
  if [[ $excess -gt 0 ]]; then
    for old in "${complete[@]:0:$excess}"; do
      echo "--> Entferne alte Sicherung $old"
      rm -rf -- "$old"
    done
  fi
fi

du -sh "$DEST" | awk '{print "==> Fertig (" $1 ")"}'
echo "    Wichtig: env.backup enthält Geheimnisse - das Zielverzeichnis entsprechend schützen."
