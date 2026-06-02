"""gRPC server для in-memory key-value хранилища с TTL и LRU eviction."""

import time
from collections import OrderedDict
from concurrent import futures
from threading import Lock

import grpc

import kvstore_pb2
import kvstore_pb2_grpc


class KeyValueStore:
    """In-memory key-value хранилище с TTL и LRU eviction."""

    def __init__(self, max_size: int = 10):
        """
        Инициализация хранилища.

        Args:
            max_size: Максимальное количество ключей в хранилище.
        """
        self.max_size = max_size
        self.store: OrderedDict[str, tuple[str, float | None]] = OrderedDict()
        self.lock = Lock()

    def _is_expired(self, expiry_time: float | None) -> bool:
        """Проверка истечения TTL."""
        if expiry_time is None:
            return False
        return time.time() > expiry_time

    def _evict_if_needed(self) -> None:
        """Удаление наименее недавно использованного ключа при превышении лимита."""
        if len(self.store) >= self.max_size:
            # Удаляем первый (наименее недавно использованный) ключ
            self.store.popitem(last=False)

    def put(self, key: str, value: str, ttl_seconds: int) -> None:
        """
        Добавить или обновить значение.

        Args:
            key: Ключ.
            value: Значение.
            ttl_seconds: TTL в секундах (0 = без TTL).
        """
        with self.lock:
            expiry_time = None
            if ttl_seconds > 0:
                expiry_time = time.time() + ttl_seconds

            # Если ключ существует, удаляем его для обновления позиции в LRU
            if key in self.store:
                del self.store[key]
            else:
                # Новый ключ - проверяем необходимость eviction
                self._evict_if_needed()

            # Добавляем в конец (помечаем как недавно использованный)
            self.store[key] = (value, expiry_time)

    def get(self, key: str) -> str | None:
        """
        Получить значение по ключу.

        Args:
            key: Ключ.

        Returns:
            Значение или None, если ключ отсутствует или истёк TTL.
        """
        with self.lock:
            if key not in self.store:
                return None

            value, expiry_time = self.store[key]

            # Проверяем TTL
            if self._is_expired(expiry_time):
                del self.store[key]
                return None

            # Обновляем позицию в LRU (перемещаем в конец)
            self.store.move_to_end(key)
            return value

    def delete(self, key: str) -> None:
        """
        Удалить ключ.

        Args:
            key: Ключ.
        """
        with self.lock:
            if key in self.store:
                del self.store[key]

    def list_with_prefix(self, prefix: str) -> list[tuple[str, str]]:
        """
        Получить все ключи и значения с заданным префиксом.

        Args:
            prefix: Префикс для фильтрации ключей.

        Returns:
            Список кортежей (ключ, значение).
        """
        with self.lock:
            result = []
            keys_to_delete = []

            for key, (value, expiry_time) in self.store.items():
                # Проверяем TTL
                if self._is_expired(expiry_time):
                    keys_to_delete.append(key)
                    continue

                # Проверяем префикс
                if key.startswith(prefix):
                    result.append((key, value))

            # Удаляем истёкшие ключи
            for key in keys_to_delete:
                del self.store[key]

            return result


class KeyValueStoreServicer(kvstore_pb2_grpc.KeyValueStoreServicer):
    """Реализация gRPC сервиса KeyValueStore."""

    def __init__(self):
        """Инициализация сервиса."""
        self.store = KeyValueStore(max_size=10)

    def Put(self, request, context):
        """Добавить или обновить значение."""
        self.store.put(request.key, request.value, request.ttl_seconds)
        return kvstore_pb2.PutResponse()

    def Get(self, request, context):
        """Получить значение по ключу."""
        value = self.store.get(request.key)
        if value is None:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"Key '{request.key}' not found or expired")
            return kvstore_pb2.GetResponse()
        return kvstore_pb2.GetResponse(value=value)

    def Delete(self, request, context):
        """Удалить ключ."""
        self.store.delete(request.key)
        return kvstore_pb2.DeleteResponse()

    def List(self, request, context):
        """Вернуть все ключи и значения с данным префиксом."""
        items = self.store.list_with_prefix(request.prefix)
        response = kvstore_pb2.ListResponse()
        for key, value in items:
            kv = response.items.add()
            kv.key = key
            kv.value = value
        return response


def serve():
    """Запуск gRPC сервера."""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    kvstore_pb2_grpc.add_KeyValueStoreServicer_to_server(KeyValueStoreServicer(), server)
    server.add_insecure_port("[::]:8000")
    server.start()
    print("Server started on port 8000")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
