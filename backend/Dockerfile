FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000
# Al arrancar: crea las tablas de control si la base es nueva y agrega columnas/tablas que falten a los tenants
# existentes (ambos pasos son idempotentes), y luego sirve la API. worker y beat usan otro comando y no migran.
CMD ["sh", "-c", "python -m app.core.init_db && python -m app.core.migrate_schema --all && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
