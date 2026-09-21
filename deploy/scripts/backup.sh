#!/bin/sh
# Respaldo de la base de datos y de los archivos subidos. Uso:  ./scripts/backup.sh
# Deja los archivos en deploy/backups y borra los de más de 14 días. Programarlo cada noche (README, «Respaldos»).
# IMPORTANTE: un respaldo que solo vive en la misma máquina no protege de que se dañe el disco: copiar
# deploy/backups a otro lado (disco externo, o Cloudflare R2 / Backblaze B2 con rclone).
set -eu
cd "$(dirname "$0")/.."
mkdir -p backups
STAMP="$(date +%Y%m%d-%H%M%S)"
docker compose exec -T db pg_dump -U vivecom -Fc vivecom > "backups/db-${STAMP}.dump"
docker compose exec -T backend tar -C /data -cf - uploads > "backups/uploads-${STAMP}.tar"
find backups -type f -mtime +14 -delete
echo "Respaldo listo: backups/db-${STAMP}.dump y backups/uploads-${STAMP}.tar"
