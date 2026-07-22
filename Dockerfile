# Combined image: Next.js + FastAPI (Railway single service)
FROM node:20-bookworm-slim AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ .
ENV NEXT_PUBLIC_API_URL=
ENV NODE_ENV=production
# Bake rewrite target for next start (must match start.sh uvicorn port)
ENV INTERNAL_API_URL=http://127.0.0.1:8180
RUN npm run build

FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements-railway.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
COPY samples/ /app/samples/
COPY backend/datasets/ /app/datasets/
COPY --from=frontend-builder /app/frontend /app/frontend

COPY start.sh /app/start.sh
RUN sed -i 's/\r$//' /app/start.sh && chmod +x /app/start.sh

ENV PYTHONUNBUFFERED=1
ENV NODE_ENV=production
ENV INTERNAL_API_URL=http://127.0.0.1:8180

CMD ["/app/start.sh"]
