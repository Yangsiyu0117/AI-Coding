# Stage 1: Build frontend
FROM node:22-alpine AS frontend-builder
WORKDIR /src/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Production backend
FROM python:3.12-slim
LABEL org.opencontainers.image.title="Deploy Platform"
LABEL org.opencontainers.image.description="Automated deployment and upgrade platform"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-client curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
COPY --from=frontend-builder /src/frontend/dist ./frontend/dist
COPY setup.sh ./

RUN mkdir -p /app/data /app/logs /app/uploads

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -sf http://localhost:8000/openapi.json || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
