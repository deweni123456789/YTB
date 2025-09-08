# === FILE: Dockerfile ===
FROM python:3.10-slim

# Install system dependencies (ffmpeg required)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy source
COPY . /app

# Expose optional port for healthchecks
EXPOSE 8080

CMD ["python", "main.py"]
