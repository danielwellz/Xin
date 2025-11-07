# syntax=docker/dockerfile:1.5
FROM node:18-slim AS base
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable
WORKDIR /app

FROM base AS builder
COPY package.json pnpm-lock.yaml .npmrc ./
COPY pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY tsconfig.json ./
COPY src ./src
COPY knowledge.txt ./knowledge.txt
RUN pnpm build

FROM base AS production
ENV NODE_ENV=production
COPY .npmrc ./
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/pnpm-lock.yaml ./pnpm-lock.yaml
COPY --from=builder /app/node_modules ./node_modules
RUN pnpm prune --prod
RUN npm rebuild sharp --unsafe-perm
COPY --from=builder /app/dist ./dist
COPY knowledge.txt ./knowledge.txt
EXPOSE 3000
CMD ["node", "dist/index.js"]
