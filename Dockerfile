FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=80 \
    LOG_VIEWER_CLIENT_API_TIMEOUT_SECONDS=180 \
    LOG_VIEWER_SERVER_KEEP_ALIVE_SECONDS=120 \
    LOG_VIEWER_STREAM_INTERVAL_SECONDS=5

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 80

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-80} --timeout-keep-alive ${LOG_VIEWER_SERVER_KEEP_ALIVE_SECONDS:-120}"]
