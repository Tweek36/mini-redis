# Mini Redis - gRPC Key-Value Store

In-memory key-value хранилище на Python с поддержкой TTL и LRU eviction, реализованное через gRPC.

## Возможности

- **In-memory хранение**: быстрое хранение данных в памяти процесса
- **TTL (Time-To-Live)**: автоматическое истечение ключей через заданное время
- **LRU Eviction**: автоматическое удаление наименее недавно использованных ключей при превышении лимита (10 ключей)
- **Потокобезопасность**: корректная обработка параллельных запросов
- **gRPC API**: эффективный протокол для клиент-серверного взаимодействия

## API

### Put
Добавить или обновить значение.
- **Параметры**: 
  - `key` (string) - ключ
  - `value` (string) - значение
  - `ttl_seconds` (int32) - TTL в секундах (0 = без TTL)

### Get
Получить значение по ключу.
- **Параметры**: `key` (string)
- **Ответ**: `value` (string)
- **Ошибка**: `NOT_FOUND` если ключ отсутствует или истёк TTL

### Delete
Удалить ключ.
- **Параметры**: `key` (string)

### List
Получить все ключи и значения с заданным префиксом.
- **Параметры**: `prefix` (string)
- **Ответ**: список `KeyValue` (key, value)
- **Примечание**: истёкшие по TTL ключи не возвращаются

## Установка

### Требования
- Python 3.8+
- pip

### Установка зависимостей

```bash
# Основные зависимости
pip install -r requirements.txt

# Для разработки (включает code quality tools)
pip install -r requirements-dev.txt
```

### Генерация кода из Protobuf

Код уже сгенерирован, но если нужно перегенерировать:

```bash
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. kvstore.proto
```

## Запуск

### Запуск сервера

```bash
python server.py
```

Сервер запустится на порту **8000**.

### Запуск тестового клиента

В отдельном терминале:

```bash
python client.py
```

Клиент выполнит серию тестов:
1. Базовые операции Put/Get
2. Проверка TTL
3. Удаление ключей
4. Фильтрация по префиксу
5. LRU eviction при превышении лимита
6. Обновление существующих ключей

## Code Quality Tools

Проект настроен с pre-commit хуками для поддержания качества кода:

```bash
# Установка pre-commit хуков
pre-commit install

# Ручной запуск проверок
pre-commit run --all-files
```

### Включённые инструменты:
- **black** - автоформатирование кода
- **isort** - сортировка импортов
- **flake8** - проверка стиля кода (PEP 8)
- **mypy** - статическая типизация
- **trailing-whitespace** - удаление пробелов в конце строк
- **end-of-file-fixer** - проверка переноса строки в конце файла

## Архитектура

### Компоненты

**server.py**:
- `KeyValueStore` - основной класс хранилища с LRU и TTL
- `KeyValueStoreServicer` - реализация gRPC сервиса
- Использует `OrderedDict` для эффективной реализации LRU
- `threading.Lock` для потокобезопасности

**client.py**:
- Тестовый клиент с набором автоматических тестов
- Демонстрирует все возможности API

### LRU Eviction

- Максимальное количество ключей: **10**
- При добавлении 11-го ключа удаляется наименее недавно использованный
- `Get` и `Put` обновляют позицию ключа в LRU (перемещают в конец)
- `Delete` и истёкшие ключи не влияют на LRU

### TTL (Time-To-Live)

- TTL указывается в секундах при `Put`
- `ttl_seconds = 0` означает отсутствие TTL (ключ не истекает)
- Истёкшие ключи:
  - Возвращают `NOT_FOUND` при `Get`
  - Не включаются в результаты `List`
  - Автоматически удаляются при обращении

## Примеры использования

### Python клиент

```python
import grpc
import kvstore_pb2
import kvstore_pb2_grpc

# Подключение к серверу
channel = grpc.insecure_channel('localhost:8000')
stub = kvstore_pb2_grpc.KeyValueStoreStub(channel)

# Put - добавить значение
stub.Put(kvstore_pb2.PutRequest(
    key='user:1',
    value='Alice',
    ttl_seconds=0  # без TTL
))

# Get - получить значение
response = stub.Get(kvstore_pb2.GetRequest(key='user:1'))
print(response.value)  # Alice

# Put с TTL
stub.Put(kvstore_pb2.PutRequest(
    key='session:abc',
    value='token123',
    ttl_seconds=3600  # истечёт через 1 час
))

# Delete - удалить ключ
stub.Delete(kvstore_pb2.DeleteRequest(key='user:1'))

# List - получить все ключи с префиксом
response = stub.List(kvstore_pb2.ListRequest(prefix='user:'))
for item in response.items:
    print(f'{item.key}: {item.value}')
```

## Структура проекта

```
mini-redis/
├── kvstore.proto           # Protobuf контракт (не менять!)
├── kvstore_pb2.py          # Сгенерированный код
├── kvstore_pb2_grpc.py     # Сгенерированный код
├── server.py               # gRPC сервер
├── client.py               # Тестовый клиент
├── requirements.txt        # Основные зависимости
├── requirements-dev.txt    # Dev зависимости
├── .pre-commit-config.yaml # Pre-commit хуки
├── pyproject.toml          # Настройки инструментов
├── .flake8                 # Настройки flake8
├── .gitignore              # Git ignore
└── README.md               # Документация
```

## Ограничения и особенности

- **Максимум ключей**: 10 (настраивается в `KeyValueStore.__init__`)
- **Порт сервера**: 8000 (не дефолтный gRPC-порт)
- **Хранение**: только в памяти (данные теряются при перезапуске)
- **Протокол**: gRPC (unencrypted, insecure channel)

## Тестирование

Запустите `client.py` для автоматического тестирования всех функций:

```bash
python client.py
```

Тесты проверяют:
- ✓ Базовые операции Put/Get
- ✓ TTL истечение
- ✓ Удаление ключей
- ✓ Фильтрация по префиксу
- ✓ LRU eviction
- ✓ Обновление существующих ключей

## Разработка

### Форматирование кода

```bash
# Автоформатирование
black server.py client.py

# Сортировка импортов
isort server.py client.py
```

### Проверка типов

```bash
mypy server.py client.py
```

### Проверка стиля

```bash
flake8 server.py client.py
```
