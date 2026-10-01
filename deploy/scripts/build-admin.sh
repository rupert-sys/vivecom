#!/bin/sh
# Compila el portal de administrador principal (staff Vivecom) apuntando a la API pública y lo deja en
# deploy/admin-dist. Ver scripts/build-panel.sh (misma receta, para el otro front-end).
#
# NUNCA lo corras en el servidor de producción de AWS: tiene ~900MB de RAM totales, compartidos con
# backend/worker/beat/db/redis ya corriendo ahí — un `npm ci` + `vite build` dentro de un contenedor extra
# le bastó al kernel para matar a `uvicorn` por out-of-memory (pasó en producción real el 2026-09-29: el
# backend estuvo caído ~3 minutos hasta que Docker lo reinició solo). Corre este script en tu máquina de
# desarrollo (o cualquiera con RAM de sobra) y sube SOLO la carpeta ya compilada:
#   ./scripts/build-admin.sh
#   rsync -az admin-dist/ ubuntu@<IP-del-servidor>:~/vivecom/deploy/admin-dist/
# Mismo riesgo aplica a build-panel.sh y build-app-web.sh — ninguno de los tres debería correr en el servidor.
#
# Uso:  ./scripts/build-admin.sh vivecom.example      (o sin argumento: lee DOMAIN de .env)
set -eu
cd "$(dirname "$0")/.."

# Salvaguarda: RAM disponible muy baja huele a la instancia pequeña de producción, no a una máquina de
# desarrollo — aborta con instrucciones en vez de arriesgarse a repetir el incidente de arriba. `free` no
# existe en macOS (ahí este riesgo no aplica igual: Docker Desktop corre en su propia VM, no compite por RAM
# del host con nada que sirva tráfico real), así que la salvaguarda solo corre en Linux.
if command -v free >/dev/null 2>&1; then
  mem_disponible_mb=$(free -m | awk '/^Mem:/ {print $7}')
  if [ "${mem_disponible_mb:-99999}" -lt 700 ]; then
    echo "Esta máquina tiene solo ${mem_disponible_mb}MB de RAM disponible — huele al servidor de producción," >&2
    echo "no a una máquina de desarrollo. Compilar aquí puede tumbar el backend por falta de memoria (ya" >&2
    echo "pasó una vez, 2026-09-29). Compílalo en otra máquina y sube solo admin-dist/ por rsync (ver el" >&2
    echo "comentario al inicio de este script). Para forzarlo de todos modos:" >&2
    echo "  FORZAR_BUILD_LOCAL=1 ./scripts/build-admin.sh" >&2
    [ "${FORZAR_BUILD_LOCAL:-}" = "1" ] || exit 1
  fi
fi

DOMAIN="${1:-$(grep '^DOMAIN=' .env | cut -d= -f2)}"
[ -n "$DOMAIN" ] || { echo "Indica el dominio: ./scripts/build-admin.sh mi-dominio.mx" >&2; exit 1; }
# Docker Desktop no se instala en el PATH por default en esta Mac (encontrado varias veces) — se agrega aquí
# para no depender de que quien corra el script ya lo haya exportado a mano.
export PATH="$HOME/.docker/bin:$PATH"
rm -rf admin-dist && mkdir -p admin-dist
docker run --rm \
  -v "$(cd .. && pwd)/staff-frontend:/src:ro" -v "$(pwd)/admin-dist:/out" \
  -e VITE_API_URL="https://api.${DOMAIN}" node:20-alpine \
  sh -c "cp -r /src /app && cd /app && rm -rf node_modules dist && npm ci --no-audit --no-fund && npm run build && cp -r dist/. /out/"
echo "Portal de administrador principal compilado para https://api.${DOMAIN} en deploy/admin-dist"
