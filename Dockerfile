FROM python:3.12-slim

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code, frontend, and data
COPY . .

# Render.com injects PORT env var; HF Spaces uses 7860; default fallback 8080
EXPOSE ${PORT:-8080}

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
