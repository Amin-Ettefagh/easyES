# Multi-stage build for the Next.js frontend.
# Uses Next's "standalone" output (see next.config.js) so the runtime image only
# ships the traced server + static assets, not the whole node_modules tree.

# ---- deps: install node_modules from lockfile-free package.json ----
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json ./
# No package-lock committed for the demo; `npm install` resolves the pinned
# versions in package.json. (In a real project you'd commit the lockfile and use
# `npm ci`.)
RUN npm install --no-audit --no-fund

# ---- builder: compile the app ----
FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# The public URL stays same-origin; Next proxies it to the Docker backend.
ARG NEXT_PUBLIC_API_BASE=/api/v1
ARG INTERNAL_API_BASE=http://backend:8000/api/v1
ENV NEXT_PUBLIC_API_BASE=$NEXT_PUBLIC_API_BASE
ENV INTERNAL_API_BASE=$INTERNAL_API_BASE
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# ---- runner: minimal runtime ----
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000

RUN addgroup --system --gid 1001 nodejs \
  && adduser --system --uid 1001 nextjs

# Standalone server + static assets.
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
CMD ["node", "server.js"]
