# Stage 1: Build React frontend
FROM node:20-slim AS node-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python runtime
FROM python:3.11-slim

# Install system dependencies: LibreOffice Writer + Playwright Chromium deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-writer \
    curl \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium only
RUN playwright install chromium --with-deps

# Copy backend
COPY backend/ ./backend/

# Copy built frontend
COPY --from=node-builder /app/frontend/dist ./frontend/dist

# Create data directory
RUN mkdir -p /data/templates /data/proposals

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
