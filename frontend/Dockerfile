# Build stage
FROM node:18-alpine AS build

WORKDIR /app

# Copy package files and install dependencies
COPY package.json package-lock.json* ./
RUN npm ci || npm install

# Copy application code
COPY . .

# Build the frontend application
# Pass the backend URL as a build arg if needed
ARG VITE_API_BASE_URL=/api/v1
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

# Serve stage using nginx
FROM nginx:alpine

# Copy built assets to nginx serving directory
COPY --from=build /app/dist /usr/share/nginx/html

# Copy custom nginx configuration (with SPA fallback, security headers, gzip, and /healthz)
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

# Health check using busybox wget against /healthz
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost/healthz || exit 1

CMD ["nginx", "-g", "daemon off;"]
