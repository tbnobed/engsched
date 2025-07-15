# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies including timezone data
RUN apt-get update && apt-get install -y \
    postgresql-client \
    build-essential \
    libpq-dev \
    curl \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Set timezone explicitly at system level
ENV DEBIAN_FRONTEND=noninteractive
RUN echo "America/Los_Angeles" > /etc/timezone && \
    ln -sf /usr/share/zoneinfo/America/Los_Angeles /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata

# Copy only requirements first to leverage Docker cache
COPY pyproject.toml .

# Install Python packages from pyproject.toml dependencies
RUN pip install --no-cache-dir \
    apscheduler>=3.11.0 \
    email-validator>=2.2.0 \
    flask>=3.1.0 \
    flask-login>=0.6.3 \
    flask-sqlalchemy>=3.1.1 \
    flask-wtf>=1.2.2 \
    gunicorn>=23.0.0 \
    markupsafe>=3.0.2 \
    openpyxl>=3.1.5 \
    psycopg2-binary>=2.9.10 \
    python-dotenv>=1.0.1 \
    pytz>=2024.2 \
    requests>=2.32.3 \
    sendgrid>=6.11.0 \
    sqlalchemy>=2.0.36 \
    trafilatura>=2.0.0 \
    werkzeug>=3.1.3 \
    wtforms>=3.2.1

# Copy application files
COPY . .

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1
ENV TZ=America/Los_Angeles

# Create required directories
RUN mkdir -p /app/static/uploads/profile_pictures /app/static/backups

# Set permissions
RUN chmod -R 755 /app/static \
    && chmod -R 777 /app/static/backups \
    && chmod -R 777 /app/static/uploads  

# Copy and set permissions for entrypoint script (do this as root before switching users)
COPY --chmod=755 docker-entrypoint.sh /app/docker-entrypoint.sh

# Create a non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 5000

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Use entrypoint script for proper database initialization
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--reuse-port", "--reload", "main:app"]