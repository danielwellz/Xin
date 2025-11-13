FROM node:20-alpine AS deps
WORKDIR /app

# Workspace metadata from repo root
COPY pnpm-workspace.yaml pnpm-workspace.yaml
COPY pnpm-lock.yaml pnpm-lock.yaml

# Frontend sources
COPY services/frontend/package.json \
     services/frontend/tsconfig.json \
     services/frontend/tsconfig.node.json \
     services/frontend/vite.config.ts \
     services/frontend/tailwind.config.ts \
     services/frontend/postcss.config.cjs \
     ./
COPY services/frontend/src ./src
COPY services/frontend/public ./public
COPY services/frontend/.storybook ./.storybook

RUN corepack enable pnpm && pnpm install --frozen-lockfile=false
RUN pnpm build

FROM nginx:1.27-alpine
COPY --from=deps /app/dist /usr/share/nginx/html
COPY services/frontend/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
