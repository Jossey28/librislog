# Stage 1: build
FROM node:22-alpine AS builder
WORKDIR /app
ARG PUBLIC_DEFAULT_LOCALE=en
ENV PUBLIC_DEFAULT_LOCALE=${PUBLIC_DEFAULT_LOCALE}
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: serve
FROM nginx:alpine
COPY --from=builder /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
