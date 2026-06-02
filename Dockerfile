# Multi-stage build для оптимизации размера образа
FROM python:3.11-slim as builder

WORKDIR /app

# Установка зависимостей для сборки
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc g++ && \
    rm -rf /var/lib/apt/lists/*

# Копирование requirements и установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Финальный образ
FROM python:3.11-slim

WORKDIR /app

# Копирование установленных пакетов из builder
COPY --from=builder /root/.local /root/.local

# Обновление PATH для использования локальных пакетов
ENV PATH=/root/.local/bin:$PATH

# Копирование кода приложения
COPY kvstore.proto .
COPY kvstore_pb2.py .
COPY kvstore_pb2_grpc.py .
COPY server.py .

# Открытие порта
EXPOSE 8000

# Запуск сервера
CMD ["python", "server.py"]