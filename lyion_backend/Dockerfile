# =============================================================================
# Dockerfile — Ly-ion Flask backend
# =============================================================================
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create non-root user for security
RUN adduser --disabled-password --gecos "" lyionuser && \
    chown -R lyionuser:lyionuser /app
USER lyionuser

EXPOSE 5000

# Use Gunicorn for production; bind to 0.0.0.0 so Nginx can proxy to it
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", \
     "--timeout", "60", "app:create_app()"]
