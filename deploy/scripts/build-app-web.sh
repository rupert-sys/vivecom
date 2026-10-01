#!/bin/sh
# Compila la app de residentes para la web (iPhone: Safari → Compartir → Añadir a pantalla de inicio) y la deja
# en deploy/app-dist, apuntando a la API pública. Requiere Flutter en el PATH.
#
# NUNCA lo corras en el servidor de producción de AWS: tiene ~900MB de RAM totales, compartidos con
# backend/worker/beat/db/redis ya corriendo ahí — un build (Flutter o `npm ci`+`vite build`) le bastó al
# kernel para matar a `uvicorn` por out-of-memory (pasó en producción real el 2026-09-29, compilando
# build-admin.sh ahí — el backend estuvo caído ~3 minutos hasta que Docker lo reinició solo). Corre este
# script en tu máquina de desarrollo y sube SOLO app-dist/ ya compilado:
#   ./scripts/build-app-web.sh && rsync -az app-dist/ ubuntu@<IP-del-servidor>:~/vivecom/deploy/app-dist/
#
# Uso:  ./scripts/build-app-web.sh vivecom.mx      (o sin argumento: lee DOMAIN de .env)
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
    echo "pasó una vez, 2026-09-29). Compílalo en otra máquina y sube solo app-dist/ por rsync (ver el" >&2
    echo "comentario al inicio de este script). Para forzarlo de todos modos:" >&2
    echo "  FORZAR_BUILD_LOCAL=1 ./scripts/build-app-web.sh" >&2
    [ "${FORZAR_BUILD_LOCAL:-}" = "1" ] || exit 1
  fi
fi

DOMAIN="${1:-$(grep '^DOMAIN=' .env | cut -d= -f2)}"
[ -n "$DOMAIN" ] || { echo "Indica el dominio: ./scripts/build-app-web.sh mi-dominio.mx" >&2; exit 1; }
# --pwa-strategy=none: sin el service worker de Flutter, que deja en cada teléfono una copia vieja hasta la visita siguiente.
(cd ../mobile && flutter build web --release --pwa-strategy=none --dart-define=API_BASE_URL="https://api.${DOMAIN}")
# Conserva los APK de Android (residentes: build-apk.sh; vigilancia: build-apk-caseta.sh) si ya existen:
# recompilar la web no debe borrarlos.
[ -f app-dist/vivecom-android.apk ] && cp app-dist/vivecom-android.apk /tmp/vivecom-android.apk.keep || rm -f /tmp/vivecom-android.apk.keep
[ -f app-dist/vivecom-caseta.apk ] && cp app-dist/vivecom-caseta.apk /tmp/vivecom-caseta.apk.keep || rm -f /tmp/vivecom-caseta.apk.keep
rm -rf app-dist && mkdir -p app-dist
cp -r ../mobile/build/web/. app-dist/
[ -f /tmp/vivecom-android.apk.keep ] && mv /tmp/vivecom-android.apk.keep app-dist/vivecom-android.apk
[ -f /tmp/vivecom-caseta.apk.keep ] && mv /tmp/vivecom-caseta.apk.keep app-dist/vivecom-caseta.apk
echo "App web compilada para https://api.${DOMAIN} en deploy/app-dist (se sirve en https://app.${DOMAIN})"
