# Vivecom

Plataforma de administración, comunicación, seguridad y pagos para condominios en México.

## Estructura del repo
```
backend/         API en FastAPI (Python), multi-tenant por schema de PostgreSQL
frontend/        Panel de administración de un condominio (React + TypeScript + Vite) —
                  instalable como PWA y empacado como app nativa de Android (frontend/android/, vía Capacitor)
staff-frontend/  Portal de administrador principal (staff Vivecom): lista y administra todos los
                  condominios, login propio sin relación con ningún tenant (admin.<dominio>)
mobile/          App de residentes (Flutter) — iOS y web (app.<dominio>)
caseta/          App de vigilancia (Flutter, Android) — escaneo de QR de visitantes/proveedores
deploy/          Despliegue de producción: Docker Compose + Caddy en una sola instancia —
                  ver deploy/README.md para el procedimiento real
design/          Sistema de diseño (paleta, tipografía, componentes)
infra/           Terraform para AWS — histórico, no es el mecanismo de despliegue actual
                  (ver deploy/README.md); se dejó sin usar al optar por una sola instancia
.github/         CI: corre lint + pytest del backend en cada push/PR
```

## Levantar el backend en local
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env   # y llena DATABASE_URL / JWT_SECRET
uvicorn app.main:app --reload
```

## Correr los tests
```bash
cd backend
pytest -v
```

## Levantar el panel admin (frontend) en local
Requiere Node.js 20+. Si no lo tienes instalado, todos los comandos de abajo
corren igual dentro de un contenedor de Docker — ver la variante de cada uno:

```bash
cd frontend
npm install
echo "VITE_API_URL=http://localhost:8000" > .env.local   # opcional, ese es el default
npm run dev      # http://localhost:5173 — necesita el backend corriendo (ver arriba)
npm test         # Vitest + React Testing Library
npm run build    # type-check (tsc -b) + build de producción
```

**Sin Node.js instalado (vía Docker):**
```bash
cd /ruta/al/repo
docker run --rm -v "$(pwd)/frontend:/app" -v vivecom_frontend_node_modules:/app/node_modules -w /app node:20-alpine npm install
docker run --rm -v "$(pwd)/frontend:/app" -v vivecom_frontend_node_modules:/app/node_modules -w /app node:20-alpine npm test
docker run --rm -v "$(pwd)/frontend:/app" -v vivecom_frontend_node_modules:/app/node_modules -p 5173:5173 -w /app node:20-alpine npm run dev -- --host 0.0.0.0
```
El volumen nombrado `vivecom_frontend_node_modules` evita instalar
`node_modules` directo en el host (evita problemas de arquitectura entre el
contenedor Linux y macOS). `.claude/launch.json` ya tiene esta variante del
dev server configurada para levantarse con un clic desde Claude Code.

El portal de administrador principal (`staff-frontend/`) se levanta y se
prueba igual que `frontend/`, apuntando al mismo backend.

Las apps de Flutter (`mobile/`, `caseta/`) requieren Flutter instalado —
`flutter run` dentro de cada carpeta.

## Desplegar a producción
El despliegue real es una sola máquina (Docker Compose + Caddy, HTTPS directo
vía Let's Encrypt), no el Terraform de `infra/`. El procedimiento completo
—incluyendo por qué nunca hay que compilar en el servidor— está en
[`deploy/README.md`](deploy/README.md).

## Documentos de referencia
- `alcance_vivecom.md` — alcance del producto, historias de usuario, decisiones de negocio.
- `modelo_datos_vivecom.md` — modelo de datos completo (ERD).
- `plan_de_trabajo_vivecom.xlsx` — backlog de las 4 fases del proyecto.
- `bitacora_vivecom.html` — bitácora cronológica de cambios del proyecto.
- `CONTRIBUTING.md` — estrategia de branching y convención de commits.

## Pendiente de configurar (requiere acción humana, no se puede automatizar desde aquí)
- Configurar la protección de la rama `main` en GitHub, según la política documentada en `CONTRIBUTING.md`.
- Confirmar que el secreto real de recepción SPEI (`STP_WEBHOOK_SECRET` en `deploy/.env`, proveedor STP/Fintoc)
  esté puesto en el servidor de producción — `backend/app/core/config.py` solo trae un valor de ejemplo por default.
