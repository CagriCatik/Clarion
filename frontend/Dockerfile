# Stage 1: Build
FROM node:20-slim as build-stage

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

# Stage 2: Serve
FROM nginx:alpine

# Copy build files
COPY --from=build-stage /app/dist /usr/share/nginx/html

# Custom nginx config for SPA routing (if needed)
RUN echo 'server { \
    listen 80; \
    location / { \
    root /usr/share/nginx/html; \
    index index.html; \
    try_files $uri $uri/ /index.html; \
    } \
    location /v1 { \
    proxy_pass http://backend:8000; \
    } \
    }' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
