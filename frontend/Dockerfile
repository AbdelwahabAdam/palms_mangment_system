# Build shared package and both React apps
FROM node:22-bookworm AS build
WORKDIR /app

COPY package.json package-lock.json ./
COPY shared/package.json ./shared/package.json
COPY public-app/package.json ./public-app/package.json
COPY admin-app/package.json ./admin-app/package.json
COPY eslint.config.js ./eslint.config.js
COPY tsconfig.json ./tsconfig.json

RUN npm ci

COPY shared ./shared
COPY public-app ./public-app
COPY admin-app ./admin-app

ENV VITE_API_BASE_URL=/api/v1
RUN npm run build --workspace=@palms/shared \
 && npm run build --workspace=@palms/public-app \
 && npm run build --workspace=@palms/admin-app

# Serve with Nginx: public at /, admin at /admin/, API proxy to backend
FROM nginx:1.27-alpine

COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/public-app/dist /usr/share/nginx/html
COPY --from=build /app/admin-app/dist /usr/share/nginx/html/admin

EXPOSE 80

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=5 \
  CMD wget -qO- http://127.0.0.1/ >/dev/null || exit 1
