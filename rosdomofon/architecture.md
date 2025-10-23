# Архитектура проекта rosdomofon-bitrix24

## Описание проекта
Интеграция между системой РосДомофон и Bitrix24 для автоматизации работы с абонентами и их аккаунтами.

## Структура файлов

### `models.py`
**Назначение**: Pydantic модели для валидации данных API РосДомофон

**Содержит**:
- **Модели авторизации**: `AuthResponse`
- **Модели аккаунтов**: `Account`, `Owner`, `Company`, `CreateAccountRequest/Response`, `AccountInfo`
- **Модели квартир**: `CreateFlatRequest/Response`, `Flat`, `FlatDetailed`, `AbonentFlat`, `FlatOwner`
- **Модели услуг**: `Service`, `ServiceInfo`, `ServiceDetailed`, `ServiceWithFullDetails`, `CreateConnectionRequest/Response`, `Connection`, `ConnectionDetailed`, `DelegationTunings`
- **Модели адресов**: `Address`, `AddressDetailed`, `Country`, `CountryDetailed`, `Street`, `StreetDetailed`, `House`, `HouseDetailed`, `Entrance`, `EntranceDetailed`, `CityObject`, `FlatRange`
- **Модели подъездов**: `EntranceWithServices`, `EntrancesResponse`
- **Модели оборудования**: `Camera`, `RDA`, `Intercom`, `Location`, `Adapter`
- **Модели сообщений**: `Message`, `MessagesResponse`, `SendMessageRequest`, `AbonentInfo`, `Pageable`, `Sort`
- **Модели Kafka**: `KafkaIncomingMessage`, `KafkaOutgoingMessage`, `KafkaAbonentInfo`, `KafkaFromAbonent`, `LocalizedPush`
- **Модели регистраций (SIGN_UPS_ALL)**: `SignUpEvent`, `SignUpAbonent`, `SignUpAddress`, `SignUpHouse`, `SignUpStreet`, `SignUpCountry`, `SignUpApplication`
- **Модели детальной информации**: `AccountInfo`, `Balance`, `Invoice`, `RecurringPayment`, `Delegation`, `OwnerDetailed`, `CompanyDetailed`

**Особенности**:
- Валидация номера телефона в формате 79131234567
- Поддержка алиасов полей для совместимости с API
- Автоматическое преобразование типов данных
- **Автоматическая конвертация int → str** в `CreateAccountRequest` для полей `number` и `phone` (решает проблему совместимости с моделями Kafka, где phone как int)
- **Автоматическая конвертация int → str** в `CreateFlatRequest` для полей `entrance_id` и `flat_number` (решает проблему совместимости с событиями регистрации Kafka)
- Отдельные модели для Kafka сообщений с поддержкой формата РосДомофон
- **Свойство `text`** в `KafkaIncomingMessage` - автоматически извлекает текст из `message` или `localizedPush.message`

### `rosdomofon.py`
**Назначение**: Основной модуль для работы с API РосДомофон

**Содержит**:
- **Класс RosDomofonAPI** с методами:
  - `authenticate()` - авторизация в системе
  - `get_accounts()` - получение всех аккаунтов
  - `get_account_info()` - получение детальной информации об аккаунте (баланс, подключения, квартиры)
  - `get_account_by_phone()` - поиск аккаунта по номеру телефона
  - `create_account()` - создание нового аккаунта
  - `create_flat()` - создание квартиры
  - `get_entrance_services()` - получение услуг подъезда
  - `connect_service()` - подключение услуги (принимает flat_id как int или str)
  - `get_account_connections()` - получение подключений аккаунта
  - `get_service_connections()` - получение подключений услуги
  - `get_abonent_flats()` - получение всех квартир абонента с полными адресами
  - `get_entrances()` - получение списка подъездов с услугами компании (с фильтрацией по адресу, поддержка параметра all для автоматической пагинации всех данных)
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
    - `set_signup_handler()` - установка обработчика событий регистрации (общий топик SIGN_UPS_ALL)
    - `start_signup_consumer()` - запуск потребления событий регистрации (общий топик)
    - `stop_signup_consumer()` - остановка потребления событий регистрации (общий топик)
    - `set_company_signup_handler()` - установка обработчика событий регистрации компании (топик SIGN_UPS_<company>)
    - `start_company_signup_consumer()` - запуск потребления событий регистрации компании
    - `stop_company_signup_consumer()` - остановка потребления событий регистрации компании

**Особенности**:
- Подробные docstring с примерами использования для каждого метода
- Автоматическое логирование операций через loguru
- Обработка ошибок HTTP запросов
- **Автоматическая переавторизация при истечении токена** - при получении 401 ошибки клиент автоматически запрашивает новый токен и повторяет запрос
- Отслеживание времени жизни токена доступа
- Импорт моделей из отдельного файла models.py
- Интегрированный Kafka клиент для real-time сообщений
- Контекстный менеджер для автоматического закрытия соединений

### `kafka_client.py`
**Назначение**: Клиент для работы с Kafka сообщениями РосДомофон

**Содержит**:
- **Класс RosDomofonKafkaClient** с методами:
  - `set_message_handler()` - установка обработчика входящих сообщений (sync/async)
  - `set_signup_handler()` - установка обработчика событий регистрации (общий топик SIGN_UPS_ALL, sync/async)
  - `set_company_signup_handler()` - установка обработчика событий регистрации компании (топик SIGN_UPS_<company>, sync/async)
  - `start_consuming()` - запуск потребления сообщений в отдельном потоке
  - `start_signup_consuming()` - запуск потребления регистраций (общий топик) в отдельном потоке
  - `start_company_signup_consuming()` - запуск потребления регистраций компании в отдельном потоке
  - `stop_consuming()` - остановка потребления сообщений
  - `stop_signup_consuming()` - остановка потребления регистраций (общий топик)
  - `stop_company_signup_consuming()` - остановка потребления регистраций компании
  - `send_message()` - отправка сообщения одному абоненту
  - `send_message_to_multiple()` - отправка группового сообщения
  - `close()` - закрытие всех соединений

**Особенности**:
- Автоматическое формирование топиков по имени компании (`MESSAGES_IN_<company>`, `MESSAGES_OUT_<company>`)
- Поддержка топика регистраций `SIGN_UPS_ALL` (общий для всех компаний)
- Поддержка топика регистраций `SIGN_UPS_<company>` (специфичный для компании)
- Работа в отдельных потоках для неблокирующего потребления сообщений и регистраций
- **Использование одной consumer group** для всех топиков (авторизация на уровне группы)
- **Поддержка асинхронных обработчиков** - автоматическое определение типа обработчика (sync/async) и корректный вызов через `asyncio.run()`
- Валидация данных через Pydantic модели
- Контекстный менеджер для безопасного закрытия
- Подробное логирование всех операций
- **Поддержка SASL_SSL аутентификации** с механизмом SCRAM-SHA-512
- **SSL сертификаты** для безопасного подключения к Kafka брокерам

### `kafka_example.py`
**Назначение**: Пример использования Kafka интеграции

**Содержит**:
- Обработчик входящих сообщений `handle_incoming_message()`
- Обработчик событий регистрации (общий топик) `handle_signup()`
- Обработчик событий регистрации компании `handle_company_signup()`
- Демонстрация работы со всеми топиками одновременно
- Примеры отправки сообщений через Kafka

**Особенности**:
- Полный цикл работы: подключение → обработка → отключение
- Обработка KeyboardInterrupt для корректного завершения
- Примеры отправки сообщений (закомментированы)
- Демонстрация работы с двумя топиками регистраций одновременно

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

# Получение детальной информации об аккаунте
account_info = api.get_account_info(904154)
print(f"Баланс: {account_info.balance.balance} {account_info.balance.currency}")
print(f"Заблокирован: {account_info.blocked}")
for conn in account_info.connections:
    print(f"Услуга: {conn.service.name}, Тариф: {conn.tariff}")

# Получение всех подъездов с автоматической пагинацией
all_entrances = api.get_entrances(all=True)
print(f"Получено {len(all_entrances.content)} подъездов из {all_entrances.total_elements}")
for entrance in all_entrances.content:
    print(f"Подъезд: {entrance.address_string}")
    for service in entrance.services:
        print(f"  - {service.name} ({service.type})")
```

#### Использование с Kafka
```python
from rosdomofon import RosDomofonAPI
from models import KafkaIncomingMessage

# Инициализация с Kafka поддержкой (с аутентификацией)
api = RosDomofonAPI(
    username="user", 
    password="pass",
    kafka_bootstrap_servers="kafka.rosdomofon.com:443",
    company_short_name="asd_asd",
    kafka_group_id="rosdomofon_group",
    kafka_username="kafka_user",
    kafka_password="kafka_pass",
    kafka_ssl_ca_cert_path="kafka-ca.crt"
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
- **Автоматическая переавторизация при 401 Unauthorized**:
  - Клиент отслеживает время истечения токена доступа
  - При получении 401 ошибки автоматически запрашивается новый токен
  - Оригинальный запрос повторяется с новым токеном без вмешательства пользователя
  - Предотвращение бесконечного цикла через флаг `retry_auth`
- Валидационные ошибки Pydantic предоставляют детальную информацию о проблемах в данных
- Все исключения пробрасываются выше для обработки в вызывающем коде
- Kafka ошибки логируются и обрабатываются с возможностью повторных попыток

## Kafka интеграция

### Настройка топиков
Для работы с Kafka необходимо:
1. Уведомить компанию РосДомофон о желании использовать Kafka
2. Получить учетные данные для подключения:
   - **Адрес Kafka брокеров**: `kafka.rosdomofon.com:443`
   - **Имя пользователя** и **пароль** для SASL аутентификации
   - **SSL сертификат** (`kafka-ca.crt`) для безопасного подключения
   - **ID группы** потребителей
3. Получить название топиков компании:
   - **Входящие сообщения**: `MESSAGES_IN_<company_short_name>`
   - **Исходящие сообщения**: `MESSAGES_OUT_<company_short_name>`
   - **События регистрации (общий)**: `SIGN_UPS_ALL` (общий топик для всех компаний)
   - **События регистрации (компании)**: `SIGN_UPS_<company_short_name>` (только регистрации в вашей компании)
4. **Для использования топиков регистраций**: явно запросить у РосДомофон доступ к нужным топикам для вашей consumer group

### Безопасность подключения
Kafka клиент поддерживает:
- **SASL_SSL протокол** для шифрования трафика
- **Механизм SCRAM-SHA-512** для аутентификации пользователей
- **SSL сертификаты CA** для проверки подлинности сервера

### Авторизация и группы потребителей
**Важно**: В Kafka авторизация настраивается на уровне **consumer group**, а не на уровне топиков.

- Все топики (`MESSAGES_IN_*`, `SIGN_UPS_ALL`, `SIGN_UPS_<company>`) используют **одну и ту же consumer group**
- Это позволяет избежать ошибок авторизации `GroupAuthorizationFailedError`
- Топики обрабатываются в **разных потоках**, но с единой группой
- При настройке доступа в Kafka нужно запросить доступ ко всем необходимым топикам для одной группы

### Формат сообщений

#### Входящие сообщения (MESSAGES_IN)
Структура реального сообщения от абонента:
```json
{
  "fromAbonent": {
    "id": 1574870,
    "phone": 79308312222,
    "companyId": 1292,
    "restrictionPushTokenIds": []
  },
  "channel": "support",
  "message": null,
  "deliveryMethod": null,
  "toAbonents": null,
  "broadcast": false,
  "waitResponse": true,
  "localizedPush": {
    "message": "Текст сообщения от абонента",
    "messageKey": null,
    "messageArgs": null
  }
}
```

**Важно**: Текст сообщения находится в `localizedPush.message`, а не в `message`. Используйте свойство `text` модели для универсального доступа к тексту.

#### Исходящие сообщения (MESSAGES_OUT)
- **Канал**: `"support"` для чата техподдержки
- **Метод доставки**: `"PUSH"` для push-уведомлений
- **Получатели**: массив с ID и/или номерами телефонов абонентов
- **Отправитель**: опциональная информация об отправителе

#### События регистрации (SIGN_UPS_ALL)
Топик содержит события регистрации новых абонентов в системе РосДомофон.

**Формат данных**:
```json
{
  "id": 566836,
  "abonent": {

  },
  "address": {
    "country": {
      "shortName": "RU",
      "name": "Россия"
    },
    "city": "Иваново",
    "street": {
      "id": 7037,
      "name": "Ташкентская",
      "codeKladr": "37000001000099700",
      "codeFias": "44c5f004-32d5-4724-9ee2-099071e88d1c"
    },
    "house": {
      "id": 65175,
      "number": "100",
      "block": "",
      "building": "",
      "housing": ""
    }
  },
  "application": {
    "id": 1,
    "name": "rd_android",
    "provider": "google",
    "companyId": 3
  },
  "virtual": false,
  "timeZone": "Europe/Moscow +03:00",
  "offerSigned": false,
  "contractNumber": "",
  "status": "UNPROCESSED",
  "createdAt": 1690216032782,
  "uid": "c7cba623-111c-4fe3-b952-1f5f9a1b7b37"
}
```

**Важные поля**:
- `abonent.id` - ID абонента для отправки приветственных сообщений
- `abonent.phone` - номер телефона
- `address.country` - страна (shortName: RU/KZ, name: полное название)
- `address.city` - город
- `address.street` - улица с кодами ФИАС/КЛАДР или universalCode
- `address.house` - номер дома с дополнительными полями (корпус, строение)
- `application` - приложение через которое зарегистрировался (rd_android, rd_ios, orion_ios и т.д.)
- `virtual` - виртуальная трубка (true) или физическая (false)
- `offerSigned` - подписана ли оферта
- `status` - статус регистрации (UNPROCESSED и др.)
- `createdAt` - timestamp создания в миллисекундах
- `uid` - уникальный идентификатор события

**Обратите внимание**: Поле `flat` (квартира) отсутствует в событиях регистрации. Номер квартиры регистрируется позже отдельно.

#### События регистрации компании (SIGN_UPS_<company>)
Топик `SIGN_UPS_<company_short_name>` содержит события регистрации **только** для конкретной компании.

**Формат данных**: Идентичен топику `SIGN_UPS_ALL`, но содержит только регистрации абонентов вашей компании.

**Отличия от SIGN_UPS_ALL**:
- `SIGN_UPS_ALL` - все регистрации во всех компаниях системы РосДомофон (требует явного запроса доступа)
- `SIGN_UPS_<company>` - только регистрации в вашей компании (обычно доступен по умолчанию)

**Когда использовать**:
- Используйте `SIGN_UPS_<company>`, если вам нужны только регистрации в вашей компании
- Используйте `SIGN_UPS_ALL`, если вы разрабатываете сервис для нескольких компаний
- Можно подписаться на оба топика одновременно для разных целей обработки

### Обработка событий регистрации

**Поддержка синхронных и асинхронных обработчиков**

Все обработчики Kafka могут быть как синхронными, так и асинхронными функциями. Клиент автоматически определяет тип функции и вызывает её корректным образом.

#### Пример 1: Обработка общих регистраций (SIGN_UPS_ALL)

**Синхронный обработчик:**

```python
from rosdomofon import RosDomofonAPI
from models import SignUpEvent

# Инициализация с Kafka
api = RosDomofonAPI(
    username="user",
    password="pass",
    kafka_bootstrap_servers="kafka.rosdomofon.com:443",
    company_short_name="asd_asd",
    kafka_group_id="rosdomofon_group",
    kafka_username="kafka_user",
    kafka_password="kafka_pass",
    kafka_ssl_ca_cert_path="kafka-ca.crt"
)

# Синхронный обработчик регистраций (общий топик)
def handle_signup(signup: SignUpEvent):
    print(f"[SIGN_UPS_ALL] Новая регистрация: {signup.abonent.phone}")
    print(f"Страна: {signup.address.country.name}")
    print(f"Адрес: {signup.address.city}, ул.{signup.address.street.name}, д.{signup.address.house.number}")
    print(f"Приложение: {signup.application.name}")
    print(f"Статус: {signup.status}")

# Установка и запуск
api.set_signup_handler(handle_signup)
api.start_signup_consumer()
```

**Асинхронный обработчик:**

```python
import asyncio
from rosdomofon import RosDomofonAPI
from models import SignUpEvent

# Асинхронный обработчик с операциями БД
async def handle_signup_async(signup: SignUpEvent):
    print(f"[SIGN_UPS_ALL] Новая регистрация: {signup.abonent.phone}")
    
    # Асинхронное сохранение в БД
    await db.save_signup(signup)
    
    # Асинхронная отправка в аналитику
    await analytics.track_event("new_signup", {
        "phone": signup.abonent.phone,
        "city": signup.address.city
    })

# Установка и запуск
api.set_signup_handler(handle_signup_async)
api.start_signup_consumer()
```

#### Пример 2: Обработка регистраций компании (SIGN_UPS_<company>)

**Синхронный обработчик:**

```python
# Синхронный обработчик регистраций компании
def handle_company_signup(signup: SignUpEvent):
    print(f"[SIGN_UPS_<company>] Новая регистрация в нашей компании: {signup.abonent.phone}")
    print(f"Адрес: {signup.address.city}, ул.{signup.address.street.name}, д.{signup.address.house.number}")
    
    # Отправить приветственное сообщение
    api.send_message_to_abonent(
        signup.abonent.id,
        'support',
        'Добро пожаловать в нашу компанию!'
    )

# Установка и запуск
api.set_company_signup_handler(handle_company_signup)
api.start_company_signup_consumer()
```

**Асинхронный обработчик:**

```python
# Асинхронный обработчик с внешними API вызовами
async def handle_company_signup_async(signup: SignUpEvent):
    print(f"[SIGN_UPS_<company>] Новая регистрация: {signup.abonent.phone}")
    
    # Асинхронная отправка приветствия через Kafka
    await api_async.send_message_async(
        signup.abonent.id,
        'support',
        'Добро пожаловать в нашу компанию!'
    )
    
    # Асинхронная регистрация в CRM
    await crm.create_contact({
        "phone": signup.abonent.phone,
        "address": f"{signup.address.city}, {signup.address.street.name}, {signup.address.house.number}"
    })

# Установка и запуск
api.set_company_signup_handler(handle_company_signup_async)
api.start_company_signup_consumer()
```

#### Пример 3: Одновременная обработка обоих топиков

**Синхронные обработчики:**

```python
# Обработка всех регистраций для аналитики
def handle_all_signups(signup: SignUpEvent):
    print(f"[Аналитика] Регистрация: {signup.abonent.phone}")
    # Отправить данные в систему аналитики
    analytics.track_signup(signup)

# Обработка только регистраций компании для приветствия
def handle_our_signups(signup: SignUpEvent):
    print(f"[Приветствие] Наш новый клиент: {signup.abonent.phone}")
    api.send_message_to_abonent(
        signup.abonent.id,
        'support',
        'Добро пожаловать! Мы рады видеть вас в нашей компании!'
    )

# Запуск обоих обработчиков
api.set_signup_handler(handle_all_signups)
api.set_company_signup_handler(handle_our_signups)
api.start_signup_consumer()
api.start_company_signup_consumer()
```

**Асинхронные обработчики:**

```python
# Асинхронная обработка всех регистраций для аналитики
async def handle_all_signups_async(signup: SignUpEvent):
    print(f"[Аналитика] Регистрация: {signup.abonent.phone}")
    
    # Асинхронная отправка в аналитику
    await analytics.track_signup_async(signup)
    
    # Асинхронное обогащение данных
    geo_data = await geo_service.get_location_info(signup.address.city)
    await analytics.track_geo(geo_data)

# Асинхронная обработка регистраций компании с комплексной логикой
async def handle_our_signups_async(signup: SignUpEvent):
    print(f"[Приветствие] Наш новый клиент: {signup.abonent.phone}")
    
    # Параллельное выполнение нескольких задач
    await asyncio.gather(
        # Отправить приветствие
        api_async.send_message(
            signup.abonent.id,
            'support',
            'Добро пожаловать! Мы рады видеть вас в нашей компании!'
        ),
        # Создать контакт в CRM
        crm.create_contact(signup),
        # Отправить email
        email_service.send_welcome_email(signup.abonent.phone)
    )

# Запуск обоих обработчиков (можно комбинировать sync и async)
api.set_signup_handler(handle_all_signups_async)
api.set_company_signup_handler(handle_our_signups_async)
api.start_signup_consumer()
api.start_company_signup_consumer()
```

### Преимущества Kafka интеграции
- **Real-time обработка** сообщений от абонентов и событий регистрации
- **Масштабируемость** - поддержка высокой нагрузки
- **Надежность** - гарантированная доставка сообщений
- **Гибкость** - возможность обработки событий несколькими сервисами
- **Автоматизация** - мгновенная реакция на регистрацию новых абонентов
- **Поддержка async/await** - возможность использования асинхронных обработчиков для:
  - Параллельного выполнения задач через `asyncio.gather()`
  - Интеграции с асинхронными БД (asyncpg, motor)
  - Асинхронных HTTP запросов (httpx, aiohttp)
  - Неблокирующей работы с внешними API
