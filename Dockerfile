# Build stage for React frontend
FROM node:18-alpine AS frontend-build

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Production stage
FROM python:3.12-slim

# Install system dependencies including ffmpeg for MoviePy
RUN apt-get update && apt-get install -y \
    ffmpeg \
    imagemagick \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Configure ImageMagick policy for MoviePy text rendering
RUN sed -i 's/rights="none" pattern="@\*"/rights="read|write" pattern="@*"/' /etc/ImageMagick-6/policy.xml || true

WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY main.py .
COPY gpt_api.py .
COPY tiktokvoice.py .
COPY server.py .
COPY moviepy_config.py .

# Copy built frontend from build stage
COPY --from=frontend-build /app/frontend/build ./static

# Create directories for videos and temp files
RUN mkdir -p videos temp

# Expose port
EXPOSE 8000

# Environment variables
ENV PYTHONUNBUFFERED=1

# Run the server
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
