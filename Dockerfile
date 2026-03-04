FROM python:3.12-slim

# Install system dependencies for Playwright browser
RUN apt-get update && apt-get install -y \
    gcc \
    ca-certificates \
    curl \
    gnupg \
    fonts-unifont \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libatspi2.0-0 \
    libpangocairo-1.0-0 \
    libgtk-3-0 \
    libglib2.0-0 \
    libevent-2.1-7 \
    libxtst6 \
    libxcursor1 \
    && rm -rf /var/lib/apt/lists/* \
    && update-ca-certificates

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium

# Copy application files
COPY app.py .
COPY page.html .

# Create data directory for SQLite
RUN mkdir -p /app/data

# Expose port
EXPOSE 8080

# Run the application
CMD ["python", "app.py"]
