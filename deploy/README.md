# Despliegue de Vivecom en una sola máquina

Sirve para la **muestra** (tu Mac) y para la **PC dedicada** que la reemplaza: es el mismo montaje. Todo el estado vive en
dos volúmenes de Docker (`pgdata`, `uploads`) y en el archivo `.env`; lo demás sale del repositorio.

```
Internet ── Cloudflare (HTTPS) ── túnel ── api.vivecom.mx    → backend   (FastAPI)
                                        ├─ panel.vivecom.mx  → panel     (Caddy, panel de administración)
                                        └─ app.vivecom.mx    → panel     (Caddy, app web de residentes para iPhone)
                       db (Postgres 16) · redis · worker + beat (Celery: cargos, recargos, seguimiento de acuerdos)
```

Nada se abre en el router: el túnel sale desde tu máquina hacia Cloudflare.

## 1. Cloudflare (una vez)
1. Agregar `vivecom.mx` a Cloudflare (plan Free) y cambiar los servidores de nombres en el registrador. Esperar a «Active».
2. Zero Trust → Networks → Tunnels → crear un túnel «Cloudflared» y copiar su **token**.
3. En el túnel, tres *Public hostnames* (tipo HTTP): `api.vivecom.mx` → `backend:8000`; `panel.vivecom.mx` → `panel:80`;
   `app.vivecom.mx` → `panel:80`.

## 2. Preparar la máquina
Requisitos: Docker (Desktop en Mac/Windows, Engine en Linux) y, para compilar la app web, Flutter.
```bash
cd deploy
cp .env.example .env        # llenar: DOMAIN=vivecom.mx, POSTGRES_PASSWORD, JWT_SECRET, STP_WEBHOOK_SECRET, CLOUDFLARE_TUNNEL_TOKEN
./scripts/build-panel.sh    # panel-dist/  (usa Docker, compila para https://api.vivecom.mx)
./scripts/build-app-web.sh  # app-dist/    (usa Flutter)
docker compose --profile tunnel up -d --build
```
Al arrancar, el backend crea las tablas de control si la base es nueva y migra los condominios existentes
(`app/core/init_db.py` + `migrate_schema --all`). Probar sin el túnel: `curl http://127.0.0.1:8010/docs`.

Primer condominio: `POST /signup` (nombre, correo y contraseña del administrador, CLABE). El administrador da de alta a
los demás usuarios desde el panel.

## 3. Que la máquina no se apague
- **Mac:** Ajustes → Batería/Energía → «Evitar que el Mac entre en reposo automáticamente cuando la pantalla está apagada»,
  conectado a la corriente. Desactivar las actualizaciones que reinician solas (o programarlas). Docker Desktop → Settings →
  «Start Docker Desktop when you sign in». Los contenedores llevan `restart: unless-stopped`: vuelven solos.
- **No usarla de máquina de desarrollo mientras sirve a usuarios:** compilar apps o correr Docker/Xcode a la vez la satura.

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
