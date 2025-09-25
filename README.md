### `rosdomofon.py`

**Назначение**: Основной модуль для работы с API РосДомофон

**Содержит**:

- **Класс RosDomofonAPI** с методами:
  - `authenticate()` - авторизация в системе
  - `get_accounts()` - получение всех аккаунтов
  - `get_account_by_phone()` - поиск аккаунта по номеру телефона
  - `create_account()` - создание нового аккаунта
  - `create_flat()` - создание квартиры
  - `get_entrance_services()` - получение услуг подъезда
  - `connect_service()` - подключение услуги
  - `get_account_connections()` - получение подключений аккаунта
  - `get_service_connections()` - получение подключений услуги
  - `block_account()` / `unblock_account()` - блокировка/разблокировка аккаунта
  - `block_connection()` / `unblock_connection()` - блокировка/разблокировка подключения
  - `send_message()` - отправка push-уведомлений (принимает словари или ID)
  - `send_message_to_abonent()` - упрощенная отправка сообщения по ID абонента
  - `get_abonent_messages()` - получение сообщений абонента
  - **Kafka методы**:
    - `set_kafka_message_handler()` - установка обработчика входящих Kafka сообщений
    - `start_kafka_consumer()` - запуск потребления сообщений из Kafka
    - `stop_kafka_consumer()` - остановка потребления сообщений
    - `send_kafka_message()` - отправка сообщения через Kafka
    - `send_kafka_message_to_multiple()` - групповая отправка через Kafka

**Особенности**:

- Подробные docstring с примерами использования для каждого метода
- Автоматическое логирование операций через loguru
- Обработка ошибок HTTP запросов
- Импорт моделей из отдельного файла models.py
- Интегрированный Kafka клиент для real-time сообщений
- Контекстный менеджер для автоматического закрытия соединений

### `kafka_client.py`

**Назначение**: Клиент для работы с Kafka сообщениями РосДомофон

**Содержит**:

- **Класс RosDomofonKafkaClient** с методами:
  - `set_message_handler()` - установка обработчика входящих сообщений
  - `start_consuming()` - запуск потребления в отдельном потоке
  - `stop_consuming()` - остановка потребления
  - `send_message()` - отправка сообщения одному абоненту
  - `send_message_to_multiple()` - отправка группового сообщения
  - `close()` - закрытие всех соединений


# пример получения аккаунта по номеру телефона

```python
account = api.get_account_by_phone(79308325215)
print(account)
print(account.owner.id) # abonent_id
print(account.id) # account_id
```

# пример получения сообщений

```python
messages = api.get_abonent_messages(abonent_id, channel='support', page=0, size=10)
print(messages)
```

# пример отправки сообщения

```python
api.send_message_to_abonent(abonent_id, 'support', f'вы написали {messages.content[0].message}')
```

# Пример использования Kafka

### Инициализация с Kafka поддержкой

```python
api = RosDomofonAPI(
    username="user", password="pass",
    kafka_bootstrap_servers="kafka.example.com:9092",
    company_short_name="SK_SB"
)
```

### Обработка входящих сообщений

```python
def handle_message(message: KafkaIncomingMessage):
    print(f"Сообщение от {message.from_abonent.phone}: {message.message}")

api.set_kafka_message_handler(handle_message)
api.start_kafka_consumer()
```

### Отправка через Kafka

```python
api.send_kafka_message(1574870, 79308312233, "Ответ через Kafka")
```
