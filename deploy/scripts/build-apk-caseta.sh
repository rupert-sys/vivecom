#!/bin/sh
# Compila el APK de Android de la app de vigilancia (caseta), firmado con la llave de release, y lo deja en
# deploy/app-dist/vivecom-caseta.apk, que Caddy sirve en https://app.<dominio>/vivecom-caseta.apk — mismo
# mecanismo que vivecom-android.apk (build-apk.sh): el matcher @archivo del Caddyfile ya sirve cualquier
# archivo con extensión reconocida desde app-dist, así que no hace falta tocar el Caddyfile ni el túnel de
# Cloudflare para agregar este archivo.
# Requiere Flutter y caseta/android/key.properties (la llave vive fuera del repositorio, igual que la de
# mobile/ — NO la reutilices sin más: genera una propia para esta app, con su propio alias/contraseña).
# Uso:  ./scripts/build-apk-caseta.sh vivecom.com.mx      (o sin argumento: lee DOMAIN de .env)
set -eu
cd "$(dirname "$0")/.."
DOMAIN="${1:-$(grep '^DOMAIN=' .env | cut -d= -f2)}"
[ -n "$DOMAIN" ] || { echo "Indica el dominio: ./scripts/build-apk-caseta.sh mi-dominio.mx" >&2; exit 1; }
[ -f ../caseta/android/key.properties ] || { echo "Falta caseta/android/key.properties (llave de firma) — ver comentario arriba." >&2; exit 1; }
(cd ../caseta && flutter build apk --release --dart-define=API_BASE_URL="https://api.${DOMAIN}")
mkdir -p app-dist
cp ../caseta/build/app/outputs/flutter-apk/app-release.apk app-dist/vivecom-caseta.apk
echo "APK listo: deploy/app-dist/vivecom-caseta.apk ($(du -h app-dist/vivecom-caseta.apk | cut -f1)) → https://app.${DOMAIN}/vivecom-caseta.apk"
