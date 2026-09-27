# syntax=docker/dockerfile:1

# --- deps: install dependencies (cached separately from source changes) ---
FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# --- builder: build the Next.js app ---
FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# `npm ci`'s postinstall already ran this in the deps stage, but COPY . . above just replaced
# public/ with the host's copy (which doesn't have these generated assets, see .gitignore) -
# run it again now so the Code Interpreter's Pyodide runtime actually ships in the image.
RUN node scripts/copy-pyodide-assets.mjs

# NEXT_PUBLIC_* vars are inlined into the client bundle at build time.
# Pass a real backend URL via --build-arg if it differs from the default
# (see web/README.md for why docker-compose.yml's `environment:` on the
# `web` service alone does NOT affect this build).
ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}

RUN npm run build

# --- runner: minimal production image ---
FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

RUN addgroup --system --gid 1001 nodejs \
  && adduser --system --uid 1001 nextjs

# output: "standalone" (see next.config.ts) traces only the files needed
# at runtime, so node_modules doesn't need to be installed here again.
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

USER nextjs
EXPOSE 3000

CMD ["node", "server.js"]
