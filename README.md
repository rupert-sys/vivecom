# Vivecom

Plataforma de administración, comunicación, seguridad y pagos para condominios en México.

## Estructura del repo
```
backend/    API en FastAPI (Python), multi-tenant por schema de PostgreSQL
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

## Pendiente de configurar (requiere acción humana, no se puede automatizar desde aquí)
- Crear el repositorio real en GitHub/GitLab y hacer el primer push de este contenido.
- Crear la cuenta de AWS y el bucket S3 para el state de Terraform.
- Configurar los secrets de GitHub Actions: `AWS_DEPLOY_ROLE_ARN`.
- Crear la cuenta con el proveedor de recepción SPEI (STP o Fintoc) y agregar sus credenciales como secreto.
