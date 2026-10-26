FROM node:20-alpine AS build
WORKDIR /app
ARG VITE_API_BASE_URL=/support
ARG VITE_BASE_PATH=/support/
ARG BACKEND_HOST=pulsesg-ai-task-manager-backend
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_BASE_PATH=$VITE_BASE_PATH
ENV BACKEND_HOST=$BACKEND_HOST
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
FROM nginx:1.27-alpine
ENV BACKEND_HOST=pulsesg-ai-task-manager-backend NGINX_ENVSUBST_FILTER=^BACKEND_HOST$
COPY nginx.conf /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
