FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json pnpm-workspace.yaml tsconfig.json tsconfig.node.json vite.config.ts tailwind.config.ts postcss.config.cjs ./
COPY src ./src
COPY public ./public
COPY .storybook ./.storybook
RUN corepack enable pnpm && pnpm install --frozen-lockfile=false
RUN pnpm build

FROM nginx:1.27-alpine
COPY --from=deps /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
