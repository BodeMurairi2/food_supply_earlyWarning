# HarvestWatch: one container serving the FastAPI backend and the built React frontend.

# 1) Build the frontend
FROM node:20-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# 2) Python runtime
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY api/requirements.txt api/requirements.txt
RUN pip install -r api/requirements.txt
COPY api/ api/
COPY models/ models/
COPY food_security_dataset.csv .
COPY --from=frontend /app/frontend/dist frontend/dist
RUN useradd --create-home app && chown -R app /app
USER app
# Render sets PORT; default to 8000 locally.
EXPOSE 8000
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
