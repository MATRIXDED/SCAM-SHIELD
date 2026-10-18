# ============================================================
# Stage 1: Build React/Vite frontend
# ============================================================
FROM node:22-alpine AS frontend-builder

WORKDIR /build/frontend

# Install deps first for better layer caching
COPY frontend/package*.json ./
RUN npm ci --prefer-offline

# Copy source and build
COPY frontend/ ./

# Build-time arg for API URL (injected, never baked secret)
ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

RUN npm run build


# ============================================================
# Stage 2: Python backend runtime
# ============================================================
FROM python:3.11-slim AS backend

# Security: run as non-root user
RUN groupadd -r scamshield && useradd -r -g scamshield -d /app -s /sbin/nologin scamshield

WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ ./backend/
COPY mcp_server/ ./mcp_server/

# Copy compiled frontend static files to serve via FastAPI StaticFiles
COPY --from=frontend-builder /build/frontend/dist ./frontend/dist

# Drop privileges
USER scamshield

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/status')" || exit 1

# Start uvicorn
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
