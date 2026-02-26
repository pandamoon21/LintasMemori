FROM node:20-alpine AS web-build
WORKDIR /src/apps/web
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci
COPY apps/web/ ./
RUN npm run build

FROM python:3.11-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY services/api ./services/api
COPY workers ./workers
COPY --from=web-build /src/apps/web/dist ./apps/web/dist

WORKDIR /app/services/api
RUN python -m pip install --upgrade pip \
    && pip install .

ENV LM_DB_PATH=/data/lintasmemori.db
ENV LM_STATIC_DIR=/app/apps/web/dist

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
