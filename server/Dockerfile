# syntax=docker/dockerfile:1
FROM node:24-bookworm-slim AS web
WORKDIR /build/web
COPY web/package*.json ./
RUN npm ci
COPY web/ ./
COPY docs/phase2/example-v2/ /build/docs/phase2/example-v2/
COPY docs/backend/contract/ /build/docs/backend/contract/
ENV VITE_API_BASE_URL=/api
RUN npm run build
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
COPY teamsync/ ./teamsync/
COPY server/ ./server/
RUN python -m pip install --no-cache-dir '.[server]' && chmod -R a+rX /app
COPY --from=web /build/web/dist ./web/dist
ENTRYPOINT ["python", "server/entrypoint.py"]
ENV PYTHONDONTWRITEBYTECODE=1
