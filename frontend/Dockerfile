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

COPY frontend/package.json frontend/package-lock.json ./
RUN npm install

COPY frontend/ .
RUN npm run build

# --- produção (servido pelo Nginx) --------------------------------------
FROM nginx:alpine AS prod

COPY --from=build /app/dist /usr/share/nginx/html
COPY docker/nginx/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
