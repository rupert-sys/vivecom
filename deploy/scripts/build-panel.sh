#!/bin/sh
# Compila el panel de administración apuntando a la API pública y lo deja en deploy/panel-dist.
# Uso:  ./scripts/build-panel.sh vivecom.example      (o sin argumento: lee DOMAIN de .env)
set -eu
cd "$(dirname "$0")/.."
DOMAIN="${1:-$(grep '^DOMAIN=' .env | cut -d= -f2)}"
[ -n "$DOMAIN" ] || { echo "Indica el dominio: ./scripts/build-panel.sh mi-dominio.mx" >&2; exit 1; }
rm -rf panel-dist && mkdir -p panel-dist
# Se copia el código a una carpeta temporal del contenedor: así node_modules de Linux no ensucia el repositorio.
docker run --rm \
  -v "$(cd .. && pwd)/frontend:/src:ro" -v "$(pwd)/panel-dist:/out" \
  -e VITE_API_URL="https://api.${DOMAIN}" node:20-alpine \
  sh -c "cp -r /src /app && cd /app && rm -rf node_modules dist && npm ci --no-audit --no-fund && npm run build && cp -r dist/. /out/"
echo "Panel compilado para https://api.${DOMAIN} en deploy/panel-dist"
