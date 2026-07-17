# syntax=docker/dockerfile:1

FROM node:24-alpine AS base

WORKDIR /app

# --- desenvolvimento ---------------------------------------------------
FROM base AS dev

COPY frontend/package.json frontend/package-lock.json ./
RUN npm install

COPY frontend/ .

EXPOSE 5173
CMD ["npm", "run", "dev"]

# --- build de produção -------------------------------------------------
FROM base AS build

# Caminho relativo: o Nginx do próprio container serve o backend na mesma
# origem (proxy /api), então o build não precisa saber domínio nenhum.
ARG VITE_API_URL=/api
ENV VITE_API_URL=$VITE_API_URL

COPY frontend/package.json frontend/package-lock.json ./
RUN npm install

COPY frontend/ .
RUN npm run build

# --- produção (gateway Nginx: SPA + proxy para o backend) ---------------
FROM nginx:alpine AS prod

COPY --from=build /app/dist /usr/share/nginx/html
COPY docker/nginx/nginx.conf.template /etc/nginx/templates/default.conf.template

EXPOSE 80 443
CMD ["nginx", "-g", "daemon off;"]
