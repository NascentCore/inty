# Minimal Cloud Run Job image for cron-style execution.
# Build with optional secrets: docker build --build-arg FOO=secret ...
# See README.md for GitHub Secrets → build-arg usage (no Secret Manager).
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
