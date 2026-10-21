FROM node:22-bookworm-slim
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend ./
EXPOSE 5173
