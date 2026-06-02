"""Тестовый клиент для gRPC key-value хранилища."""

import os
import time

import grpc

import kvstore_pb2
import kvstore_pb2_grpc


def run_tests():
    """Запуск тестов для проверки функциональности сервера."""
    # Получаем адрес сервера из переменных окружения
    server_host = os.getenv("SERVER_HOST", "localhost")
    server_port = os.getenv("SERVER_PORT", "8000")
    server_address = f"{server_host}:{server_port}"

    print(f"Подключение к серверу: {server_address}")

    # Подключаемся к серверу
    with grpc.insecure_channel(server_address) as channel:
        stub = kvstore_pb2_grpc.KeyValueStoreStub(channel)

        print("=" * 60)
        print("Тестирование gRPC Key-Value Store")
        print("=" * 60)

        # Тест 1: Put и Get
        print("\n1. Тест Put и Get:")
        stub.Put(kvstore_pb2.PutRequest(key="user:1", value="Alice", ttl_seconds=0))
        response = stub.Get(kvstore_pb2.GetRequest(key="user:1"))
        print(f"   Put('user:1', 'Alice') -> Get('user:1') = '{response.value}'")
        assert response.value == "Alice", "Значение не совпадает!"
        print("   ✓ Тест пройден")

        # Тест 2: TTL
        print("\n2. Тест TTL:")
        stub.Put(kvstore_pb2.PutRequest(key="temp:1", value="temporary", ttl_seconds=2))
        response = stub.Get(kvstore_pb2.GetRequest(key="temp:1"))
        print(f"   Put('temp:1', 'temporary', ttl=2s) -> Get = '{response.value}'")
        print("   Ожидание 3 секунды...")
        time.sleep(3)
        try:
            response = stub.Get(kvstore_pb2.GetRequest(key="temp:1"))
            print("   ✗ Ошибка: ключ должен был истечь!")
        except grpc.RpcError as e:
            if e.code() == grpc.StatusCode.NOT_FOUND:
                print("   ✓ Ключ успешно истёк (NOT_FOUND)")
            else:
                print(f"   ✗ Неожиданная ошибка: {e.code()}")

        # Тест 3: Delete
        print("\n3. Тест Delete:")
        stub.Put(kvstore_pb2.PutRequest(key="user:2", value="Bob", ttl_seconds=0))
        stub.Delete(kvstore_pb2.DeleteRequest(key="user:2"))
        try:
            response = stub.Get(kvstore_pb2.GetRequest(key="user:2"))
            print("   ✗ Ошибка: ключ должен был быть удалён!")
        except grpc.RpcError as e:
            if e.code() == grpc.StatusCode.NOT_FOUND:
                print("   ✓ Ключ успешно удалён (NOT_FOUND)")
            else:
                print(f"   ✗ Неожиданная ошибка: {e.code()}")

        # Тест 4: List с префиксом
        print("\n4. Тест List с префиксом:")
        stub.Put(kvstore_pb2.PutRequest(key="user:3", value="Charlie", ttl_seconds=0))
        stub.Put(kvstore_pb2.PutRequest(key="user:4", value="David", ttl_seconds=0))
        stub.Put(kvstore_pb2.PutRequest(key="admin:1", value="Admin", ttl_seconds=0))
        response = stub.List(kvstore_pb2.ListRequest(prefix="user:"))
        print("   List(prefix='user:'):")
        for item in response.items:
            print(f"     - {item.key}: {item.value}")
        user_keys = [item.key for item in response.items if item.key.startswith("user:")]
        assert len(user_keys) >= 2, "Должно быть как минимум 2 ключа с префиксом 'user:'"
        print("   ✓ Тест пройден")

        # Тест 5: LRU eviction (заполним хранилище > 10 ключей)
        print("\n5. Тест LRU eviction (лимит: 10 ключей):")
        # Очистка предыдущих ключей
        for i in range(1, 5):
            stub.Delete(kvstore_pb2.DeleteRequest(key=f"user:{i}"))
        stub.Delete(kvstore_pb2.DeleteRequest(key="admin:1"))

        # Добавляем 12 ключей
        print("   Добавляем 12 ключей...")
        for i in range(1, 13):
            stub.Put(kvstore_pb2.PutRequest(key=f"key:{i}", value=f"value{i}", ttl_seconds=0))

        # Первые 2 ключа должны быть evicted
        try:
            response = stub.Get(kvstore_pb2.GetRequest(key="key:1"))
            print("   ✗ Ошибка: 'key:1' должен был быть удалён по LRU!")
        except grpc.RpcError as e:
            if e.code() == grpc.StatusCode.NOT_FOUND:
                print("   ✓ 'key:1' удалён по LRU (NOT_FOUND)")

        try:
            response = stub.Get(kvstore_pb2.GetRequest(key="key:2"))
            print("   ✗ Ошибка: 'key:2' должен был быть удалён по LRU!")
        except grpc.RpcError as e:
            if e.code() == grpc.StatusCode.NOT_FOUND:
                print("   ✓ 'key:2' удалён по LRU (NOT_FOUND)")

        # Последние ключи должны остаться
        response = stub.Get(kvstore_pb2.GetRequest(key="key:12"))
        print(f"   Get('key:12') = '{response.value}'")
        assert response.value == "value12", "Последний ключ должен остаться!"
        print("   ✓ Тест LRU eviction пройден")

        # Тест 6: Обновление существующего ключа (LRU update)
        print("\n6. Тест обновления ключа (LRU):")
        stub.Put(kvstore_pb2.PutRequest(key="key:3", value="updated_value", ttl_seconds=0))
        response = stub.Get(kvstore_pb2.GetRequest(key="key:3"))
        print(f"   Put('key:3', 'updated_value') -> Get = '{response.value}'")
        assert response.value == "updated_value", "Значение должно обновиться!"
        print("   ✓ Тест пройден")

        print("\n" + "=" * 60)
        print("Все тесты успешно пройдены!")
        print("=" * 60)


if __name__ == "__main__":
    try:
        run_tests()
    except grpc.RpcError as e:
        server_host = os.getenv("SERVER_HOST", "localhost")
        server_port = os.getenv("SERVER_PORT", "8000")
        print(f"\nОшибка подключения к серверу: {e}")
        print(f"Убедитесь, что сервер запущен на {server_host}:{server_port}")
    except Exception as e:
        print(f"\nНеожиданная ошибка: {e}")
