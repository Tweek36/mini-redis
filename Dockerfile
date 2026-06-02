# Multi-stage build для оптимизации размера образа
FROM python:3.11-slim as builder

WORKDIR /app

# Установка зависимостей для сборки
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc g++ && \
    rm -rf /var/lib/apt/lists/*

# Копирование requirements и установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Финальный образ
FROM python:3.11-slim

WORKDIR /app

# Копирование установленных пакетов из builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Копирование proto файла и сервера
COPY kvstore.proto .
COPY server.py .

# Генерация Python кода из protobuf
RUN python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. kvstore.proto

# Открытие порта
EXPOSE 8000

# Запуск сервера
CMD ["python", "server.py"]
