FROM node:22-bookworm-slim AS dependencies

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

FROM node:22-bookworm-slim AS builder

ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
ARG BETTER_AUTH_URL=http://localhost:3000
ARG BETTER_AUTH_SECRET=container-build-placeholder-secret-not-for-production

ENV NEXT_TELEMETRY_DISABLED=1 \
    NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL \
    BETTER_AUTH_URL=$BETTER_AUTH_URL \
    BETTER_AUTH_SECRET=$BETTER_AUTH_SECRET

WORKDIR /app

COPY --from=dependencies /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:22-bookworm-slim AS runner

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3000

WORKDIR /app

RUN groupadd --system app && useradd --system --gid app --home-dir /app app

COPY --from=builder --chown=app:app /app/.next/standalone ./
COPY --from=builder --chown=app:app /app/.next/static ./.next/static

USER app

EXPOSE 3000

CMD ["node", "server.js"]
