FROM node:24.17.0-alpine3.23 AS frontend-build

WORKDIR /frontend

ARG NPM_CONFIG_REGISTRY
ARG NPM_CONFIG_REPLACE_REGISTRY_HOST

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/eslint.config.mjs frontend/next.config.ts frontend/postcss.config.mjs frontend/tsconfig.json frontend/vitest.config.ts ./
COPY frontend/public ./public
COPY frontend/src ./src

RUN npm run lint && npm run test:unit && npm run build

FROM ghcr.io/astral-sh/uv:0.11.28-python3.14-trixie-slim@sha256:b6e3a8825dfb232a6b962228f0b5cf98ee1d2b4263f62c2639f68887f4e634a2

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_HTTP_TIMEOUT=120 \
    UV_LINK_MODE=copy

COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY backend/app ./app
COPY --from=frontend-build /frontend/out ./app/static

EXPOSE 8000

CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
