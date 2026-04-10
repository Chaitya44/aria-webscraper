FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies needed by Camoufox (Firefox-based)
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libxext6 \
    libxfixes3 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    xdg-utils \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Fetch the Camoufox browser binary
RUN python -m camoufox fetch

# Copy application code
COPY main.py .

# Expose port for Hugging Face Spaces
EXPOSE 7860

# Run the server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
