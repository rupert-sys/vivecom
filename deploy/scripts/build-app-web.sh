#!/bin/sh
# Compila la app de residentes para la web (iPhone: Safari → Compartir → Añadir a pantalla de inicio) y la deja
# en deploy/app-dist, apuntando a la API pública. Requiere Flutter en el PATH.
# Uso:  ./scripts/build-app-web.sh vivecom.mx      (o sin argumento: lee DOMAIN de .env)
set -eu
cd "$(dirname "$0")/.."
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
