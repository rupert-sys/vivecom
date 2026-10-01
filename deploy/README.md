# Despliegue de Vivecom en una sola máquina

Sirve para la **muestra** (tu Mac) y para la **PC dedicada** que la reemplaza: es el mismo montaje. Todo el estado vive en
dos volúmenes de Docker (`pgdata`, `uploads`) y en el archivo `.env`; lo demás sale del repositorio.

```
Internet ── Cloudflare (HTTPS) ── túnel ── api.vivecom.com.mx → backend   (FastAPI)
                                        ├─ panel.vivecom.com.mx → panel     (Caddy, panel de administración)
                                        └─ app.vivecom.com.mx → panel     (Caddy, app web de residentes para iPhone)
                       db (Postgres 16) · redis · worker + beat (Celery: cargos, recargos, seguimiento de acuerdos)
```

Nada se abre en el router: el túnel sale desde tu máquina hacia Cloudflare.

## 1. Cloudflare (una vez)
El dominio (aquí `vivecom.com.mx`) debe estar en Cloudflare. El túnel se crea con la CLI y **una autorización tuya en el
navegador**: no hay que pegar tokens ni contraseñas en ningún lado.
```bash
cd deploy && mkdir -p cloudflared && chmod 777 cloudflared
cf() { docker run --rm -v "$PWD/cloudflared:/home/nonroot/.cloudflared" cloudflare/cloudflared:latest "$@"; }
cf tunnel login                                   # imprime un enlace: abrirlo, elegir el dominio y «Authorize»
cf tunnel create vivecom                          # deja el <ID>.json de credenciales en cloudflared/
for h in api panel app; do cf tunnel route dns vivecom $h.vivecom.com.mx; done
cp cloudflared.config.example.yml cloudflared/config.yml     # poner el ID del túnel y el dominio
```
`deploy/cloudflared/` (certificado, credenciales y `config.yml`) NO se sube al repositorio. Para mudarse de máquina se
copia esa carpeta junto con el `.env`: el mismo túnel funciona en la PC nueva sin tocar el DNS.

## 2. Preparar la máquina
Requisitos: Docker (Desktop en Mac/Windows, Engine en Linux) y, para compilar la app web, Flutter.
```bash
cd deploy
cp .env.example .env        # llenar: DOMAIN=vivecom.com.mx, POSTGRES_PASSWORD, JWT_SECRET, STP_WEBHOOK_SECRET
./scripts/build-panel.sh    # panel-dist/  (usa Docker, compila para https://api.<DOMAIN>)
./scripts/build-app-web.sh  # app-dist/    (usa Flutter)
./scripts/build-admin.sh    # admin-dist/  (usa Docker, portal de administrador principal — staff Vivecom)
docker compose --profile tunnel up -d --build
```

**Importante — nunca compiles en el servidor pequeño (instancia AWS de producción, ~900MB de RAM):**
`build-panel.sh`/`build-app-web.sh`/`build-admin.sh` corren un `npm ci`/`flutter build` dentro de un
contenedor extra — en una máquina con esa poca RAM, compitiendo con backend/worker/beat/db/redis ya
corriendo, eso puede hacer que el kernel mate a `uvicorn` por falta de memoria (pasó de verdad en
producción, 2026-09-29: el backend estuvo caído unos minutos hasta que Docker lo reinició solo). Los tres
scripts ya traen una salvaguarda que aborta solos si detectan poca RAM disponible (se puede forzar con
`FORZAR_BUILD_LOCAL=1`, pero no hay motivo real para hacerlo). La forma segura de actualizar cualquiera de
los tres en el servidor real: compilarlo en tu máquina de desarrollo y subir solo la carpeta `*-dist/` ya
lista por `rsync`:
```bash
./scripts/build-admin.sh                                              # en tu máquina
rsync -az admin-dist/ ubuntu@<IP-del-servidor>:~/vivecom/deploy/admin-dist/
```
Al arrancar, el backend crea las tablas de control si la base es nueva y migra los condominios existentes
(`app/core/init_db.py` + `migrate_schema --all`). Probar sin el túnel: `curl http://127.0.0.1:8010/docs`.

Primer condominio: `POST /signup` (nombre, correo y contraseña del administrador, CLABE). El administrador da de alta a
los demás usuarios, y los edita o da de baja, desde el panel (Usuarios).

**Condominio de muestra** (10 usuarios inventados y editables, reglamento de Arequipa, viviendas con y sin adeudo):
```bash
cd ../backend && python -m app.core.seed_muestra --api http://127.0.0.1:8010 --salida ../deploy/credenciales-muestra.md
```
Las contraseñas quedan en `deploy/credenciales-muestra.md` (no se sube al repositorio).

## 3. Que la máquina no se apague
- **Mac:** Ajustes → Batería/Energía → «Evitar que el Mac entre en reposo automáticamente cuando la pantalla está apagada»,
  conectado a la corriente. Desactivar las actualizaciones que reinician solas (o programarlas). Docker Desktop → Settings →
  «Start Docker Desktop when you sign in». Los contenedores llevan `restart: unless-stopped`: vuelven solos.
- **No usarla de máquina de desarrollo mientras sirve a usuarios:** compilar apps o correr Docker/Xcode a la vez la satura.
- Mientras dure la muestra, `caffeinate -i -s -m &` evita el reposo (solo mientras el proceso viva y con corriente conectada).

## 4. Respaldos (obligatorio)
```bash
./scripts/backup.sh          # deja db-*.dump y uploads-*.tar en backups/ y borra los de más de 14 días
```
Programarlo cada noche (`crontab -e`: `0 3 * * * cd /ruta/a/vivecom/deploy && ./scripts/backup.sh`) y **copiar `backups/` a otro
lado** (disco externo, o Cloudflare R2 / Backblaze B2 con `rclone`). Un respaldo en el mismo disco no protege de que el disco falle.

## 5. Trasladar a la PC dedicada
El dominio y las URLs no cambian, así que ni el panel ni las apps ni los teléfonos se tocan.
1. **En la PC:** instalar Docker, clonar el repositorio, copiar el `.env` **tal cual** (mismas claves: cambiar `JWT_SECRET`
   cerraría todas las sesiones y `POSTGRES_PASSWORD` debe coincidir con el respaldo).
2. **En la Mac:** `./scripts/backup.sh` y llevar `db-*.dump` y `uploads-*.tar` a la PC.
3. **En la PC:** `./scripts/build-panel.sh`, `./scripts/build-app-web.sh` y
   `./scripts/restore.sh backups/db-….dump backups/uploads-….tar` (levanta todo menos el túnel).
4. **Corte:** en la Mac `docker compose --profile tunnel down`; en la PC `docker compose --profile tunnel up -d`.
   El mismo token del túnel funciona en la PC: Cloudflare enruta al que esté conectado, sin cambiar DNS.
5. Verificar con el inicio de sesión de un usuario y apagar la Mac como servidor. Conservar el último respaldo unos días.

Se ensayó el traslado completo (respaldo → borrar la base y los archivos → restaurar): el inicio de sesión, los datos
y los archivos subidos volvieron intactos.

## Lo que esto NO es
Una sola máquina sin alta disponibilidad: si se apaga, el servicio cae hasta que vuelva. Sirve para una muestra y un piloto
chico. Con cobros reales de muchos condominios, pasar a un VPS o a la nube (ver `infra/`) con los mismos contenedores.
Las notificaciones de WhatsApp/SMS (Twilio) y el cobro automático por SPEI (STP) necesitan sus cuentas y credenciales:
mientras no las haya, no funcionan (el efectivo y los comprobantes sí).
