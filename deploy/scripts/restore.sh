#!/bin/sh
# Restaura un respaldo en ESTA máquina (p. ej. la PC dedicada). BORRA lo que haya en la base de datos.
# Uso:  ./scripts/restore.sh backups/db-YYYYMMDD-HHMMSS.dump backups/uploads-YYYYMMDD-HHMMSS.tar
set -eu
cd "$(dirname "$0")/.."
[ $# -eq 2 ] || { echo "Uso: $0 <db.dump> <uploads.tar>" >&2; exit 1; }
docker compose up -d db backend
docker compose exec -T db dropdb -U vivecom --if-exists vivecom
docker compose exec -T db createdb -U vivecom vivecom
docker compose exec -T db pg_restore -U vivecom -d vivecom --no-owner < "$1"
docker compose exec -T backend tar -C /data -xf - < "$2"
docker compose up -d
echo "Restaurado. Revisa:  curl http://127.0.0.1:8010/docs"
