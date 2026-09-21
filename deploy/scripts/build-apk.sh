#!/bin/sh
# Compila el APK de Android (firmado con la llave de release) apuntando a la API pública y lo deja en
# deploy/app-dist/vivecom-android.apk, que Caddy sirve en https://app.<dominio>/vivecom-android.apk.
# Requiere Flutter y mobile/android/key.properties (la llave vive fuera del repositorio; ver README).
# Uso:  ./scripts/build-apk.sh vivecom.com.mx      (o sin argumento: lee DOMAIN de .env)
set -eu
cd "$(dirname "$0")/.."
DOMAIN="${1:-$(grep '^DOMAIN=' .env | cut -d= -f2)}"
[ -n "$DOMAIN" ] || { echo "Indica el dominio: ./scripts/build-apk.sh mi-dominio.mx" >&2; exit 1; }
[ -f ../mobile/android/key.properties ] || { echo "Falta mobile/android/key.properties (llave de firma)" >&2; exit 1; }
(cd ../mobile && flutter build apk --release --dart-define=API_BASE_URL="https://api.${DOMAIN}")
mkdir -p app-dist
cp ../mobile/build/app/outputs/flutter-apk/app-release.apk app-dist/vivecom-android.apk
echo "APK listo: deploy/app-dist/vivecom-android.apk ($(du -h app-dist/vivecom-android.apk | cut -f1)) → https://app.${DOMAIN}/vivecom-android.apk"
