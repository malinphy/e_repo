# ==========================================
# Stage 1: Frontend Build Environment
# ==========================================
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy dependencies definitions
COPY frontend/package*.json ./

# Install packages
RUN npm ci

# Copy frontend source files
COPY frontend/ ./

# Build optimized production bundle to /app/frontend/dist
RUN npm run build


# ==========================================
# Stage 2: Unified Production Runner
# ==========================================
FROM python:3.12-slim AS runner

WORKDIR /app

# Python runtime configuration
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOST=0.0.0.0 \
    PORT=8000

# Install curl for container healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ ./backend

# Copy compiled frontend static assets from stage 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Create persistent storage directory for SQLite databases
RUN mkdir -p /app/backend/data

# Mark database directory as volume
VOLUME /app/backend/data

# Expose HTTP port
EXPOSE 8000

# Container healthcheck probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start FastAPI application
CMD ["python", "-m", "backend.main"]

