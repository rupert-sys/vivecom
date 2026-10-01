#!/bin/sh
# Compila el APK de Android del panel (administrador/tesorero/vocero/comité), firmado con la llave de
# release, y lo deja en deploy/app-dist/vivecom-panel.apk, que Caddy sirve en
# https://app.<dominio>/vivecom-panel.apk — mismo mecanismo que vivecom-android.apk/vivecom-caseta.apk.
#
# A diferencia de mobile/ y caseta/ (apps Flutter nativas), el panel es el MISMO React de siempre
# (frontend/), empacado con Capacitor (frontend/android/) — ver frontend/capacitor.config.ts. No usa Docker
# como build-panel.sh: Capacitor necesita Gradle + un JDK + el Android SDK reales del host, no solo Node.
#
# Requiere en esta máquina (ya presentes si mobile/caseta ya compilan APKs aquí):
#   - El JDK de Android Studio (Contents/jbr) — Gradle 9.3.1 no corre con un JDK más nuevo que ese.
#   - El Android SDK (~/Library/Android/sdk).
#   - Node (para `npm run build`/`npx cap sync`) — se usa el mismo node:20-alpine vía Docker que build-panel.sh.
#   - frontend/android/key.properties (la llave vive fuera del repositorio, igual que mobile/caseta — NO la
#     reutilices sin más: genera una propia para esta app, con su propio alias/contraseña).
#
# Uso:  ./scripts/build-apk-panel.sh vivecom.com.mx      (o sin argumento: lee DOMAIN de .env)
set -eu
cd "$(dirname "$0")/.."
DOMAIN="${1:-$(grep '^DOMAIN=' .env | cut -d= -f2)}"
[ -n "$DOMAIN" ] || { echo "Indica el dominio: ./scripts/build-apk-panel.sh mi-dominio.mx" >&2; exit 1; }
[ -f ../frontend/android/key.properties ] || { echo "Falta frontend/android/key.properties (llave de firma)" >&2; exit 1; }

JAVA_HOME="/Applications/Android Studio.app/Contents/jbr/Contents/Home"
[ -d "$JAVA_HOME" ] || { echo "No se encontró el JDK de Android Studio en $JAVA_HOME" >&2; exit 1; }
export JAVA_HOME
export ANDROID_HOME="$HOME/Library/Android/sdk"
# Docker Desktop no se instala en el PATH por default en esta Mac (encontrado repetidas veces en esta sesión)
# — se agrega aquí para que este script no dependa de que quien lo corra ya lo haya exportado a mano.
export PATH="$JAVA_HOME/bin:$ANDROID_HOME/platform-tools:$HOME/.docker/bin:$PATH"

echo "1/3 — Compilando el web (apuntando a https://api.${DOMAIN})…"
rm -rf ../frontend/dist
docker run --rm \
  -v "$(cd ../frontend && pwd):/app" -w /app \
  -e VITE_API_URL="https://api.${DOMAIN}" node:20-alpine \
  sh -c "npm ci --no-audit --no-fund && npm run build"

echo "2/3 — Sincronizando con el proyecto Android (Capacitor)…"
docker run --rm -v "$(cd ../frontend && pwd):/app" -w /app node:20-alpine sh -c "npx cap sync android"

echo "3/3 — Compilando el APK firmado (Gradle, puede tardar varios minutos la primera vez)…"
(cd ../frontend/android && ./gradlew assembleRelease)

mkdir -p app-dist
cp ../frontend/android/app/build/outputs/apk/release/app-release.apk app-dist/vivecom-panel.apk
echo "APK listo: deploy/app-dist/vivecom-panel.apk ($(du -h app-dist/vivecom-panel.apk | cut -f1)) → https://app.${DOMAIN}/vivecom-panel.apk"
