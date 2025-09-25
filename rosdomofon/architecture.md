# Архитектура проекта rosdomofon-bitrix24

## Описание проекта

Интеграция между системой РосДомофон и Bitrix24 для автоматизации работы с абонентами и их аккаунтами.

## Структура файлов

### `models.py`

**Назначение**: Pydantic модели для валидации данных API РосДомофон

**Содержит**:

- **Модели авторизации**: `AuthResponse`
- **Модели аккаунтов**: `Account`, `Owner`, `Company`, `CreateAccountRequest/Response`
- **Модели квартир**: `CreateFlatRequest/Response`
- **Модели услуг**: `Service`, `CreateConnectionRequest/Response`, `Connection`
- **Модели сообщений**: `Message`, `MessagesResponse`, `SendMessageRequest`, `AbonentInfo`, `Pageable`, `Sort`
- **Модели Kafka**: `KafkaIncomingMessage`, `KafkaOutgoingMessage`, `KafkaAbonentInfo`, `KafkaFromAbonent`

**Особенности**:

- Валидация номера телефона в формате 79131234567
- Поддержка алиасов полей для совместимости с API
- Автоматическое преобразование типов данных
- Отдельные модели для Kafka сообщений с поддержкой формата РосДомофон

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

**Особенности**:

- Автоматическое формирование топиков по имени компании (`MESSAGES_IN_<company>`, `MESSAGES_OUT_<company>`)
- Работа в отдельном потоке для неблокирующего потребления
- Валидация сообщений через Pydantic модели
- Контекстный менеджер для безопасного закрытия
- Подробное логирование всех операций

### `bitrixWork.py`

**Назначение**: Модуль для работы с API Bitrix24
**Статус**: Заглушка, требует реализации

### `main.py`

**Назначение**: Точка входа в приложение
**Содержит**: Основную логику интеграции между РосДомофон и Bitrix24

### `pyproject.toml`

**Назначение**: Конфигурация проекта и зависимостей

**Зависимости**:

- `pydantic>=2.0.0` - валидация данных
- `requests>=2.28.0` - HTTP клиент
- `loguru>=0.7.0` - логирование
- `python-dotenv>=1.1.1` - работа с переменными окружения
- `kafka-python>=2.0.0` - клиент для Apache Kafka

### `README.md`

**Назначение**: Документация проекта

## Принципы работы

### Валидация данных

Все входящие и исходящие данные проходят валидацию через Pydantic модели, что обеспечивает:

- Типобезопасность
- Автоматическое преобразование типов
- Валидацию форматов (например, номера телефонов)
- Удобный доступ к атрибутам через точечную нотацию

### Пример использования

#### Базовое использование REST API

```python
from rosdomofon import RosDomofonAPI

# Инициализация клиента
api = RosDomofonAPI(username="user", password="pass")

# Авторизация
auth = api.authenticate()

# Получение сообщений абонента
messages = api.get_abonent_messages(abonent_id=123456)

# Доступ к данным через атрибуты (благодаря Pydantic моделям)
phone = messages.content[0].abonent.phone
message_text = messages.content[0].message
total_messages = messages.total_elements

# Создание аккаунта с валидацией
response = api.create_account("ACC123456", "79061234567")
account_id = response.id
```

#### Использование с Kafka

```python
from rosdomofon import RosDomofonAPI
from models import KafkaIncomingMessage

# Инициализация с Kafka поддержкой
api = RosDomofonAPI(
    username="user", 
    password="pass",
    kafka_bootstrap_servers="kafka.example.com:9092",
    company_short_name="SK_SB",
    kafka_group_id="rosdomofon_group"
)

# Обработчик входящих сообщений
def handle_kafka_message(message: KafkaIncomingMessage):
    print(f"Получено от {message.from_abonent.phone}: {message.message}")
  
    # Автоответ через REST API
    api.send_message_to_abonent(
        message.from_abonent.id, 
        'support', 
        f'Получено ваше сообщение: {message.message}'
    )

# Установка обработчика и запуск
api.set_kafka_message_handler(handle_kafka_message)
api.start_kafka_consumer()

# Отправка через Kafka
api.send_kafka_message(
    to_abonent_id=1574870,
    to_abonent_phone=79308312222,
    message="Сообщение через Kafka"
)

# Контекстный менеджер для автоматического закрытия
with RosDomofonAPI(username="user", password="pass") as api:
    auth = api.authenticate()
    accounts = api.get_accounts()
```

### Логирование

Все операции логируются через библиотеку loguru:

- INFO уровень для основных операций
- DEBUG уровень для детальной информации
- ERROR уровень для ошибок

### Обработка ошибок

- HTTP ошибки автоматически обрабатываются и логируются
- Валидационные ошибки Pydantic предоставляют детальную информацию о проблемах в данных
- Все исключения пробрасываются выше для обработки в вызывающем коде
- Kafka ошибки логируются и обрабатываются с возможностью повторных попыток

## Kafka интеграция

### Настройка топиков

Для работы с Kafka необходимо:

1. Уведомить компанию РосДомофон о желании использовать Kafka
2. Получить название топиков компании:
   - **Входящие сообщения**: `MESSAGES_IN_<company_short_name>`
   - **Исходящие сообщения**: `MESSAGES_OUT_<company_short_name>`

### Формат сообщений

- **Канал**: `"support"` для чата техподдержки
- **Метод доставки**: `"PUSH"` для push-уведомлений
- **Получатели**: массив с ID и/или номерами телефонов абонентов
- **Отправитель**: опциональная информация об отправителе

### Преимущества Kafka интеграции

- **Real-time обработка** сообщений от абонентов
- **Масштабируемость** - поддержка высокой нагрузки
- **Надежность** - гарантированная доставка сообщений
- **Гибкость** - возможность обработки сообщений несколькими сервисами
