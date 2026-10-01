FROM node:22-bookworm-slim AS web
WORKDIR /app
COPY package.json package-lock.json ./
COPY apps/web/package.json apps/web/package.json
COPY apps/renderer/package.json apps/renderer/package.json
COPY packages/schemas/package.json packages/schemas/package.json
COPY packages/prompts/package.json packages/prompts/package.json
RUN npm ci
COPY apps/web apps/web
COPY packages packages
ENV NEXT_PUBLIC_API_BASE_URL="" NEXT_TELEMETRY_DISABLED=1
RUN npm run build:web

FROM python:3.12-slim-bookworm
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 DATA_DIR=/var/data APP_ENV=production COOKIE_SECURE=true LEGACY_LOCAL_API=false
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg libnss3 libdbus-1-3 libatk1.0-0 libgbm1 libasound2 libxrandr2 \
    libxkbcommon0 libxfixes3 libxcomposite1 libxdamage1 libatk-bridge2.0-0 \
    libpango-1.0-0 libcairo2 libcups2 fonts-noto-cjk fonts-noto-color-emoji \
    ca-certificates && rm -rf /var/lib/apt/lists/*
COPY --from=web /usr/local/bin/node /usr/local/bin/node
COPY --from=web /app/node_modules /app/node_modules
COPY package.json package-lock.json ./
COPY apps/api/requirements.lock apps/api/requirements.lock
RUN pip install --no-cache-dir -r apps/api/requirements.lock
COPY apps/api apps/api
COPY apps/renderer apps/renderer
COPY packages packages
COPY scripts scripts
COPY --from=web /app/apps/web/out apps/web/out
RUN node node_modules/@remotion/cli/remotion-cli.js browser ensure
RUN python scripts/make_demo.py
ENV PYTHONPATH=/app/apps/api WEB_DIST=/app/apps/web/out
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
