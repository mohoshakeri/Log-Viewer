FROM mirror-docker.runflare.com/library/python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_INDEX_URL=https://mirror-pypi.runflare.com/simple \

WORKDIR /app

# Configure APT mirrors for any future Debian package installs.
RUN sed -i 's/deb.debian.org/mirror-linux.runflare.com/g' /etc/apt/sources.list.d/debian.sources \
    && sed -i 's/security.debian.org/mirror-linux.runflare.com/g' /etc/apt/sources.list.d/debian.sources \
    && sed -i 's/https/http/g' /etc/apt/sources.list.d/debian.sources

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 80

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-80} --timeout-keep-alive ${LOG_VIEWER_SERVER_KEEP_ALIVE_SECONDS:-120}"]
