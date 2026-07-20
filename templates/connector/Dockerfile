FROM python:3.11-slim

WORKDIR /app

# Install dependencies first so the layer caches when only source changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080
CMD ["gunicorn", "--config", "gunicorn_config.py", "main:app"]
