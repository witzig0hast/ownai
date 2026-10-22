#!/usr/bin/env bash
# Stellt eine mit scripts/backup.sh erstellte Sicherung wieder her.
#
#   scripts/restore.sh backups/2026-10-22_031500
#   scripts/restore.sh backups/2026-10-22_031500 --yes   (ohne Rückfrage)
#
# ÜBERSCHREIBT die aktuelle Datenbank und alle erzeugten Dateien. Die .env wird NICHT
# überschrieben - das Skript warnt aber, wenn ihr SECRET_KEY nicht zur Sicherung passt (dann
# wären gespeicherte Zugangsdaten nicht mehr entschlüsselbar; in dem Fall env.backup aus der
# Sicherung als .env übernehmen).
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="${1:-}"
ASSUME_YES="${2:-}"

if [[ -z "$SRC" ]]; then
  echo "Aufruf: $0 <sicherungsverzeichnis> [--yes]" >&2
  exit 1
fi
SRC="$(cd "$SRC" && pwd)"
cd "$REPO_DIR"

for f in db.dump files.tar.gz COMPLETE; do
  if [[ ! -f "$SRC/$f" ]]; then
    echo "Fehler: $SRC/$f fehlt - keine vollständige Sicherung." >&2
    exit 1
  fi
done

env_value() {
  grep -E "^$1=" "$2" | tail -n1 | cut -d= -f2- | sed -e 's/^"//' -e 's/"$//'
}
PG_USER="$(env_value POSTGRES_USER .env)"
PG_DB="$(env_value POSTGRES_DB .env)"
: "${PG_USER:?POSTGRES_USER fehlt in .env}"
: "${PG_DB:?POSTGRES_DB fehlt in .env}"

if [[ -f "$SRC/env.backup" ]] && [[ "$(env_value SECRET_KEY .env)" != "$(env_value SECRET_KEY "$SRC/env.backup")" ]]; then
  echo "WARNUNG: SECRET_KEY in .env unterscheidet sich von dem in der Sicherung."
  echo "         Gespeicherte Zugangsdaten (CalDAV, Home Assistant, SMTP/IMAP, ...) lassen sich"
  echo "         dann nicht entschlüsseln. Normalerweise willst du vorher:"
  echo "           cp \"$SRC/env.backup\" .env"
fi

if [[ "$ASSUME_YES" != "--yes" ]]; then
  read -r -p "Aktuelle Datenbank und Dateien durch $SRC ersetzen? [ja/N] " answer
  if [[ "$answer" != "ja" ]]; then
    echo "Abgebrochen."
    exit 1
  fi
fi

echo "==> Stoppe backend und web (keine Schreibzugriffe während des Restores)"
docker compose stop backend web
docker compose up -d postgres
until docker compose exec -T postgres pg_isready -U "$PG_USER" >/dev/null 2>&1; do sleep 1; done

echo "--> Datenbank"
# --clean --if-exists ersetzt vorhandene Objekte; --no-owner, damit ein anderer POSTGRES_USER
# als beim Backup kein Problem ist.
docker compose exec -T postgres pg_restore -U "$PG_USER" -d "$PG_DB" --clean --if-exists --no-owner < "$SRC/db.dump"

echo "--> Erzeugte Dateien"
docker compose run --rm --no-deps -T backend \
  sh -c 'rm -rf /app/data/files && mkdir -p /app/data && tar -C /app/data -xzf -' < "$SRC/files.tar.gz"

echo "==> Starte backend und web"
# Der Backend-Start führt `alembic upgrade head` aus - eine Sicherung von einem älteren Stand wird
# dabei automatisch auf das aktuelle Schema gehoben.
docker compose up -d backend web
echo "==> Wiederherstellung abgeschlossen."
