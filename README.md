

![PyPI - Downloads](https://img.shields.io/pypi/dm/rosdomofon)
[![Socket Badge](https://badge.socket.dev/pypi/package/rosdomofon/0.1.8?artifact_id=tar-gz)](https://badge.socket.dev/pypi/package/rosdomofon/0.1.8?artifact_id=tar-gz)
# Поддержка и развитие
Проект активно развивается. Вопросы и предложения по улучшению приветствуются через Issues.

### `rosdomofon.py`

**Документация росдомофона [https://rdba.rosdomofon.com/swagger-ui.html#/]()**

**Назначение**: Основной модуль для работы с API РосДомофон

**Содержит**:

- **Класс RosDomofonAPI** с методами:
  - `authenticate()` - авторизация в системе
  - `update_signup()` - обновление статуса заявки регистрации
  - `get_accounts()` - получение всех аккаунтов
  - `get_account_by_phone()` - поиск аккаунта по номеру телефона
  - `create_account()` - создание нового аккаунта
  - `create_flat()` - создание квартиры
  - `get_entrance_services()` - получение услуг подъезда
  - `connect_service()` - подключение услуги
  - `get_account_connections()` - получение подключений аккаунта
  - `get_service_connections()` - получение подключений услуги
  - `get_abonent_flats()` - получение всех квартир абонента с полными адресами
  - `get_entrances()` - получение списка подъездов с услугами компании (с фильтрацией по адресу)
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
from rosdomofon import RosDomofonAPI
api = RosDomofonAPI(
    username="user", 
    password="pass",
)
api.authenticate()
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

# пример получения квартир абонента

```python
# Получить все квартиры абонента
flats = api.get_abonent_flats(1574870)
print(f"Всего квартир: {len(flats)}")

for flat in flats:
    print(f"ID квартиры: {flat.id}")
    print(f"Квартира {flat.address.flat}, подъезд {flat.address.entrance.number}")
    print(f"Адрес: {flat.address.city}, {flat.address.street.name} {flat.address.house.number}")
    print(f"Виртуальная: {flat.virtual}")
    print(f"Владелец: {flat.owner.id}")
    print("---")
```

# пример получения подъездов с услугами

```python
# Получить все подъезды компании
entrances = api.get_entrances()
print(f"Всего подъездов: {entrances.total_elements}")

# Поиск подъездов по адресу с пагинацией
entrances = api.get_entrances(address="Москва, Ленина", page=0, size=10)
for entrance in entrances.content:
    print(f"Подъезд {entrance.id}: {entrance.address_string}")
    for service in entrance.services:
        print(f"  - Услуга: {service.name} ({service.type})")
        print(f"    Камеры: {len(service.cameras)}")
        print(f"    RDA устройства: {len(service.rdas)}")
        print(f"    Тариф: {service.tariff}")
```

# Пример использования Kafka

### Инициализация с Kafka поддержкой

```python
from rosdomofon.rosdomofon import RosDomofonAPI
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
# short name company
для получения short name company нужно получить все аккаунты и найти short name company
https://rdba.rosdomofon.com/abonents-service/api/v1/accounts

```python
accounts = api.get_accounts()
for account in accounts:
    print(account.company.short_name)
```

# company id
для получения company id нужно получить все аккаунты и найти company id