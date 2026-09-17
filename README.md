# Vivecom

Plataforma de administración, comunicación, seguridad y pagos para condominios en México.

## Estructura del repo
```
backend/    API en FastAPI (Python), multi-tenant por schema de PostgreSQL
frontend/   Panel admin (React + TypeScript + Vite)
infra/      Infraestructura como código (Terraform, AWS)
design/     Sistema de diseño (paleta, tipografía, componentes)
.github/    Pipeline de CI/CD (GitHub Actions)
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

## Desplegar infraestructura (requiere cuenta de AWS propia)
```bash
cd infra
terraform init -backend-config="bucket=TU_BUCKET_DE_STATE" -backend-config="key=vivecom/staging.tfstate"
terraform plan -var="environment=staging" -var="db_password=$TF_VAR_db_password"
terraform apply
```

## Documentos de referencia
- `alcance_vivecom.md` — alcance del producto, historias de usuario, decisiones de negocio.
- `modelo_datos_vivecom.md` — modelo de datos completo (ERD).
- `plan_de_trabajo_vivecom.xlsx` — backlog de las 4 fases del proyecto.
- `CONTRIBUTING.md` — estrategia de branching y convención de commits (F0-13).

## Pendiente de configurar (requiere acción humana, no se puede automatizar desde aquí)
- Crear el repositorio real en GitHub/GitLab y hacer el primer push de este contenido
  (ya es un repo git local, con `main` como rama inicial — ver `CONTRIBUTING.md`).
- Configurar la protección de la rama `main` en el repositorio real, según la política
  documentada en `CONTRIBUTING.md`.
- Crear la cuenta de AWS y el bucket S3 para el state de Terraform.
- Configurar los secrets de GitHub Actions: `AWS_DEPLOY_ROLE_ARN`.
- Crear la cuenta con el proveedor de recepción SPEI (STP o Fintoc) y agregar sus credenciales como secreto.
