FROM node:20-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:20-slim AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build

FROM node:20-slim AS runner
WORKDIR /app
ENV NODE_ENV=production
# Docker setzt HOSTNAME automatisch auf die Container-ID; der Next.js-Standalone-Server
# bindet sich sonst daran statt an alle Interfaces, wodurch er von außen nicht erreichbar ist.
ENV HOSTNAME=0.0.0.0
# kein public/-Ordner vorhanden – bei Bedarf hier "COPY --from=builder /app/public ./public" ergänzen
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000
CMD ["node", "server.js"]
