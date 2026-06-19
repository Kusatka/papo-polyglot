# Единый образ для Gateway, сервисов лаб (lab1/lab2) и утилитарного контейнера.
# Каждый сервис запускается как отдельный контейнер со своей командой uvicorn,
# поэтому требование «каждая лаба — отдельный сервис в контейнере» выполнено,
# а образ переиспользуется (DRY, быстрая сборка).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# curl — для healthcheck'ов и отладки; затем зависимости
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Порты: gateway=8000, lab1=8001, lab2=8002 (конкретный задаётся командой)
EXPOSE 8000 8001 8002

# По умолчанию — Gateway; в docker-compose команда переопределяется для каждой роли.
CMD ["uvicorn", "gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
