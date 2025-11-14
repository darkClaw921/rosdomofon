"""
Клиент для работы с Kafka сообщениями РосДомофон
"""
import json
import threading
import time
import inspect
import asyncio
from typing import Callable, Optional, Dict, Any
from kafka import KafkaConsumer, KafkaProducer, TopicPartition
from loguru import logger

from .models import KafkaIncomingMessage, KafkaOutgoingMessage, KafkaAbonentInfo, KafkaFromAbonent, SignUpEvent


class RosDomofonKafkaClient:
    """Клиент для работы с Kafka сообщениями РосДомофон"""
    
    def __init__(self, 
                 bootstrap_servers: str = "localhost:9092",
                 company_short_name: str = "",
                 group_id: Optional[str] = None,
                 username: Optional[str] = None,
                 password: Optional[str] = None,
                 ssl_ca_cert_path: Optional[str] = None):
        """
        Инициализация Kafka клиента
        
        Args:
            bootstrap_servers (str): Адрес Kafka брокеров
            company_short_name (str): Короткое название компании для формирования топиков
            group_id (str, optional): ID группы потребителей
            username (str, optional): Имя пользователя для SASL аутентификации
            password (str, optional): Пароль для SASL аутентификации
            ssl_ca_cert_path (str, optional): Путь к SSL сертификату CA
            
        Example:
            >>> kafka_client = RosDomofonKafkaClient(
            ...     bootstrap_servers="kafka.rosdomofon.com:443",
            ...     company_short_name="Video_SB",
            ...     group_id="rosdomofon_group",
            ...     username="kafka_user",
            ...     password="kafka_pass",
            ...     ssl_ca_cert_path="/path/to/kafka-ca.crt"
            ... )
        """
        self.bootstrap_servers = bootstrap_servers
        self.company_short_name = company_short_name
        self.group_id = group_id or f"rosdomofon_{company_short_name}_group"
        self.username = username
        self.password = password
        self.ssl_ca_cert_path = ssl_ca_cert_path
        
        # Формирование названий топиков
        self.incoming_topic = f"MESSAGES_IN_{company_short_name}"
        self.outgoing_topic = f"MESSAGES_OUT_{company_short_name}"
        self.signups_topic = "SIGN_UPS_ALL"
        self.company_signups_topic = f"SIGN_UPS_{company_short_name}"
        
        self.consumer: Optional[KafkaConsumer] = None
        self.signups_consumer: Optional[KafkaConsumer] = None
        self.company_signups_consumer: Optional[KafkaConsumer] = None
        self.producer: Optional[KafkaProducer] = None
        self._consumer_thread: Optional[threading.Thread] = None
        self._signups_consumer_thread: Optional[threading.Thread] = None
        self._company_signups_consumer_thread: Optional[threading.Thread] = None
        self._running = False
        self._signups_running = False
        self._company_signups_running = False
        self._message_handler: Optional[Callable] = None
        self._signup_handler: Optional[Callable] = None
        self._company_signup_handler: Optional[Callable] = None
        
        logger.info(f"Инициализация Kafka клиента для компании {company_short_name}")
        logger.info(f"Топик входящих сообщений: {self.incoming_topic}")
        logger.info(f"Топик исходящих сообщений: {self.outgoing_topic}")
        logger.info(f"Топик регистраций (общий): {self.signups_topic}")
        logger.info(f"Топик регистраций (компании): {self.company_signups_topic}")
        
        # Проверка доступных топиков
        self._check_available_topics()
    
    def _call_handler(self, handler: Callable, data: Any):
        """
        Универсальный вызов обработчика (синхронного или асинхронного)
        
        Args:
            handler: Функция-обработчик (sync или async)
            data: Данные для передачи в обработчик
        """
        if inspect.iscoroutinefunction(handler):
            # Асинхронный обработчик - запускаем через asyncio.run()
            try:
                asyncio.run(handler(data))
            except Exception as e:
                logger.error(f"Ошибка выполнения асинхронного обработчика: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
        else:
            # Синхронный обработчик - вызываем напрямую
            try:
                handler(data)
            except Exception as e:
                logger.error(f"Ошибка выполнения синхронного обработчика: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
    
    def _create_consumer(self) -> KafkaConsumer:
        """Создать Kafka consumer"""
        config = {
            'bootstrap_servers': self.bootstrap_servers,
            'group_id': self.group_id,
            'auto_offset_reset': 'earliest',  # Читать с начала, если нет сохраненного offset
            'enable_auto_commit': True,
            'value_deserializer': lambda x: json.loads(x.decode('utf-8')),
            'consumer_timeout_ms': 1000,
            'api_version': (0, 10, 0),
            'request_timeout_ms': 30000,
            'session_timeout_ms': 10000,
            'heartbeat_interval_ms': 3000,
        }
        
        # Добавление SSL/SASL конфигурации при наличии учетных данных
        if self.username and self.password:
            config.update({
                'security_protocol': 'SASL_SSL',
                'sasl_mechanism': 'SCRAM-SHA-512',
                'sasl_plain_username': self.username,
                'sasl_plain_password': self.password,
                'ssl_check_hostname': True,
            })
            
            if self.ssl_ca_cert_path:
                config['ssl_cafile'] = self.ssl_ca_cert_path
                logger.info(f"Используется SSL сертификат: {self.ssl_ca_cert_path}")
            else:
                # Если нет сертификата, пропускаем проверку SSL
                config['ssl_check_hostname'] = False
                import ssl
                config['ssl_context'] = ssl.create_default_context()
                config['ssl_context'].check_hostname = False
                config['ssl_context'].verify_mode = ssl.CERT_NONE
                logger.warning("Проверка SSL сертификата отключена")
            
            logger.info(f"Подключение к Kafka с SASL_SSL аутентификацией (пользователь: {self.username})")
        
        return KafkaConsumer(self.incoming_topic, **config)
    
    def _create_producer(self) -> KafkaProducer:
        """Создать Kafka producer"""
        config = {
            'bootstrap_servers': self.bootstrap_servers,
            'value_serializer': lambda x: json.dumps(x, ensure_ascii=False).encode('utf-8'),
            'acks': 'all',
            'retries': 3,
            'api_version': (0, 10, 0),
            'request_timeout_ms': 30000,
        }
        
        # Добавление SSL/SASL конфигурации при наличии учетных данных
        if self.username and self.password:
            config.update({
                'security_protocol': 'SASL_SSL',
                'sasl_mechanism': 'SCRAM-SHA-512',
                'sasl_plain_username': self.username,
                'sasl_plain_password': self.password,
                'ssl_check_hostname': True,
            })
            
            if self.ssl_ca_cert_path:
                config['ssl_cafile'] = self.ssl_ca_cert_path
            else:
                # Если нет сертификата, пропускаем проверку SSL
                config['ssl_check_hostname'] = False
                import ssl
                config['ssl_context'] = ssl.create_default_context()
                config['ssl_context'].check_hostname = False
                config['ssl_context'].verify_mode = ssl.CERT_NONE
            
            logger.info(f"Producer подключается с SASL_SSL аутентификацией")
        
        return KafkaProducer(**config)
    
    def _check_available_topics(self):
        """Проверка доступных топиков в Kafka"""
        try:
            logger.info("Проверка доступных топиков...")
            temp_consumer = self._create_consumer()
            topics = temp_consumer.topics()
            temp_consumer.close()
            
            logger.info(f"Доступные топики Kafka ({len(topics)} шт.):")
            for topic in sorted(topics):
                logger.info(f"  - {topic}")
            
            # Проверяем наличие нужных топиков
            if self.incoming_topic in topics:
                logger.info(f"✓ Топик {self.incoming_topic} найден")
            else:
                logger.warning(f"✗ Топик {self.incoming_topic} не найден")
                
            if self.outgoing_topic in topics:
                logger.info(f"✓ Топик {self.outgoing_topic} найден")
            else:
                logger.warning(f"✗ Топик {self.outgoing_topic} не найден")
            
            if self.signups_topic in topics:
                logger.info(f"✓ Топик {self.signups_topic} найден")
            else:
                logger.warning(f"✗ Топик {self.signups_topic} не найден")
            
            if self.company_signups_topic in topics:
                logger.info(f"✓ Топик {self.company_signups_topic} найден")
            else:
                logger.warning(f"✗ Топик {self.company_signups_topic} не найден")
                
        except Exception as e:
            logger.error(f"Ошибка при получении списка топиков: {e}")
    
    def set_message_handler(self, handler: Callable[[KafkaIncomingMessage], None]):
        """
        Установить обработчик входящих сообщений (синхронный или асинхронный)
        
        Args:
            handler (Callable): Функция для обработки входящих сообщений (sync или async)
            
        Example:
            >>> # Синхронный обработчик
            >>> def handle_message(message: KafkaIncomingMessage):
            ...     print(f"Получено сообщение от {message.from_abonent.phone}: {message.message}")
            >>> 
            >>> # Асинхронный обработчик
            >>> async def handle_message_async(message: KafkaIncomingMessage):
            ...     await some_async_operation()
            ...     print(f"Получено сообщение от {message.from_abonent.phone}: {message.message}")
            >>> 
            >>> kafka_client.set_message_handler(handle_message)
            >>> # или
            >>> kafka_client.set_message_handler(handle_message_async)
        """
        self._message_handler = handler
        handler_type = "асинхронный" if inspect.iscoroutinefunction(handler) else "синхронный"
        logger.info(f"Установлен {handler_type} обработчик входящих сообщений")
    
    def set_signup_handler(self, handler: Callable[[SignUpEvent], None]):
        """
        Установить обработчик событий регистрации из общего топика SIGN_UPS_ALL (синхронный или асинхронный)
        
        Args:
            handler (Callable): Функция для обработки событий регистрации (sync или async)
            
        Example:
            >>> # Синхронный обработчик
            >>> def handle_signup(signup: SignUpEvent):
            ...     print(f"Новая регистрация абонента {signup.abonent.phone}")
            ...     print(f"Адрес: {signup.address.city}, {signup.address.street.name}")
            >>> 
            >>> # Асинхронный обработчик
            >>> async def handle_signup_async(signup: SignUpEvent):
            ...     await db.save_signup(signup)
            ...     print(f"Новая регистрация абонента {signup.abonent.phone}")
            >>> 
            >>> kafka_client.set_signup_handler(handle_signup)
            >>> # или
            >>> kafka_client.set_signup_handler(handle_signup_async)
        """
        self._signup_handler = handler
        handler_type = "асинхронный" if inspect.iscoroutinefunction(handler) else "синхронный"
        logger.info(f"Установлен {handler_type} обработчик событий регистрации (общий топик)")
    
    def set_company_signup_handler(self, handler: Callable[[SignUpEvent], None]):
        """
        Установить обработчик событий регистрации из топика компании SIGN_UPS_<company_short_name> (синхронный или асинхронный)
        
        Args:
            handler (Callable): Функция для обработки событий регистрации компании (sync или async)
            
        Example:
            >>> # Синхронный обработчик
            >>> def handle_company_signup(signup: SignUpEvent):
            ...     print(f"Новая регистрация компании: {signup.abonent.phone}")
            ...     print(f"Адрес: {signup.address.city}, {signup.address.street.name}")
            >>> 
            >>> # Асинхронный обработчик
            >>> async def handle_company_signup_async(signup: SignUpEvent):
            ...     await send_welcome_message(signup.abonent.id)
            ...     print(f"Новая регистрация компании: {signup.abonent.phone}")
            >>> 
            >>> kafka_client.set_company_signup_handler(handle_company_signup)
            >>> # или
            >>> kafka_client.set_company_signup_handler(handle_company_signup_async)
        """
        self._company_signup_handler = handler
        handler_type = "асинхронный" if inspect.iscoroutinefunction(handler) else "синхронный"
        logger.info(f"Установлен {handler_type} обработчик событий регистрации (топик компании)")
    
    def start_consuming(self):
        """
        Запустить потребление сообщений в отдельном потоке
        
        Example:
            >>> kafka_client.start_consuming()
            >>> # Сообщения будут обрабатываться в фоне
        """
        if self._running:
            logger.warning("Потребление уже запущено")
            return
        
        if not self._message_handler:
            raise ValueError("Необходимо установить обработчик сообщений через set_message_handler()")
        
        self._running = True
        self.consumer = self._create_consumer()
        self._consumer_thread = threading.Thread(target=self._consume_messages, daemon=True)
        self._consumer_thread.start()
        
        logger.info("Запущено потребление сообщений из Kafka")
    
    def stop_consuming(self):
        """
        Остановить потребление сообщений
        
        Example:
            >>> kafka_client.stop_consuming()
        """
        if not self._running:
            logger.warning("Потребление не запущено")
            return
        
        self._running = False
        
        if self.consumer:
            self.consumer.close()
            self.consumer = None
        
        if self._consumer_thread and self._consumer_thread.is_alive():
            self._consumer_thread.join(timeout=5)
        
        logger.info("Остановлено потребление сообщений из Kafka")
    
    def start_signup_consuming(self):
        """
        Запустить потребление событий регистрации в отдельном потоке
        
        Example:
            >>> kafka_client.start_signup_consuming()
            >>> # События регистрации будут обрабатываться в фоне
        """
        if self._signups_running:
            logger.warning("Потребление регистраций уже запущено")
            return
        
        if not self._signup_handler:
            raise ValueError("Необходимо установить обработчик регистраций через set_signup_handler()")
        
        self._signups_running = True
        
        # Создаем отдельный consumer для топика регистраций
        # Используем ту же группу, что и для сообщений - авторизация дается на группу, а не на топик
        config = {
            'bootstrap_servers': self.bootstrap_servers,
            'group_id': self.group_id,
            'auto_offset_reset': 'earliest',
            'enable_auto_commit': True,
            'value_deserializer': lambda x: json.loads(x.decode('utf-8')),
            'consumer_timeout_ms': 1000,
            'api_version': (0, 10, 0),
            'request_timeout_ms': 30000,
            'session_timeout_ms': 10000,
            'heartbeat_interval_ms': 3000,
        }
        
        if self.username and self.password:
            config.update({
                'security_protocol': 'SASL_SSL',
                'sasl_mechanism': 'SCRAM-SHA-512',
                'sasl_plain_username': self.username,
                'sasl_plain_password': self.password,
                'ssl_check_hostname': True,
            })
            
            if self.ssl_ca_cert_path:
                config['ssl_cafile'] = self.ssl_ca_cert_path
            else:
                config['ssl_check_hostname'] = False
                import ssl
                config['ssl_context'] = ssl.create_default_context()
                config['ssl_context'].check_hostname = False
                config['ssl_context'].verify_mode = ssl.CERT_NONE
        
        self.signups_consumer = KafkaConsumer(self.signups_topic, **config)
        self._signups_consumer_thread = threading.Thread(target=self._consume_signups, daemon=True)
        self._signups_consumer_thread.start()
        
        logger.info("Запущено потребление событий регистрации из Kafka")
    
    def stop_signup_consuming(self):
        """
        Остановить потребление событий регистрации
        
        Example:
            >>> kafka_client.stop_signup_consuming()
        """
        if not self._signups_running:
            logger.warning("Потребление регистраций не запущено")
            return
        
        self._signups_running = False
        
        if self.signups_consumer:
            self.signups_consumer.close()
            self.signups_consumer = None
        
        if self._signups_consumer_thread and self._signups_consumer_thread.is_alive():
            self._signups_consumer_thread.join(timeout=5)
        
        logger.info("Остановлено потребление событий регистрации из Kafka")
    
    def start_company_signup_consuming(self):
        """
        Запустить потребление событий регистрации компании в отдельном потоке
        
        Example:
            >>> kafka_client.start_company_signup_consuming()
            >>> # События регистрации компании будут обрабатываться в фоне
        """
        if self._company_signups_running:
            logger.warning("Потребление регистраций компании уже запущено")
            return
        
        if not self._company_signup_handler:
            raise ValueError("Необходимо установить обработчик регистраций компании через set_company_signup_handler()")
        
        self._company_signups_running = True
        
        # Создаем отдельный consumer для топика регистраций компании
        config = {
            'bootstrap_servers': self.bootstrap_servers,
            'group_id': self.group_id,
            'auto_offset_reset': 'earliest',
            'enable_auto_commit': True,
            'value_deserializer': lambda x: json.loads(x.decode('utf-8')),
            'consumer_timeout_ms': 1000,
            'api_version': (0, 10, 0),
            'request_timeout_ms': 30000,
            'session_timeout_ms': 10000,
            'heartbeat_interval_ms': 3000,
        }
        
        if self.username and self.password:
            config.update({
                'security_protocol': 'SASL_SSL',
                'sasl_mechanism': 'SCRAM-SHA-512',
                'sasl_plain_username': self.username,
                'sasl_plain_password': self.password,
                'ssl_check_hostname': True,
            })
            
            if self.ssl_ca_cert_path:
                config['ssl_cafile'] = self.ssl_ca_cert_path
            else:
                config['ssl_check_hostname'] = False
                import ssl
                config['ssl_context'] = ssl.create_default_context()
                config['ssl_context'].check_hostname = False
                config['ssl_context'].verify_mode = ssl.CERT_NONE
        
        self.company_signups_consumer = KafkaConsumer(self.company_signups_topic, **config)
        self._company_signups_consumer_thread = threading.Thread(target=self._consume_company_signups, daemon=True)
        self._company_signups_consumer_thread.start()
        
        logger.info("Запущено потребление событий регистрации компании из Kafka")
    
    def stop_company_signup_consuming(self):
        """
        Остановить потребление событий регистрации компании
        
        Example:
            >>> kafka_client.stop_company_signup_consuming()
        """
        if not self._company_signups_running:
            logger.warning("Потребление регистраций компании не запущено")
            return
        
        self._company_signups_running = False
        
        if self.company_signups_consumer:
            self.company_signups_consumer.close()
            self.company_signups_consumer = None
        
        if self._company_signups_consumer_thread and self._company_signups_consumer_thread.is_alive():
            self._company_signups_consumer_thread.join(timeout=5)
        
        logger.info("Остановлено потребление событий регистрации компании из Kafka")

    def fetch_latest_signups(self,
                             limit: int = 10,
                             company: bool = False,
                             timeout_seconds: float = 5.0) -> list[SignUpEvent]:
        """
        Получить последние N событий регистрации без запуска фонового потока.

        Args:
            limit (int): Количество регистраций (по умолчанию 10)
            company (bool): True — читать из топика компании, False — общий
            timeout_seconds (float): Максимальное время ожидания данных

        Returns:
            list[SignUpEvent]: Список последних регистраций (от старых к новым)
        """
        if limit <= 0:
            raise ValueError("limit должен быть положительным")

        topic = self.company_signups_topic if company else self.signups_topic
        logger.info(f"Запрос последних {limit} регистраций из топика {topic}")

        config = {
            'bootstrap_servers': self.bootstrap_servers,
            'auto_offset_reset': 'latest',
            'enable_auto_commit': False,
            'value_deserializer': lambda x: json.loads(x.decode('utf-8')),
            'consumer_timeout_ms': 1000,
            'api_version': (0, 10, 0),
            'request_timeout_ms': 30000,
            'session_timeout_ms': 10000,
            'heartbeat_interval_ms': 3000,
        }

        if self.username and self.password:
            config.update({
                'security_protocol': 'SASL_SSL',
                'sasl_mechanism': 'SCRAM-SHA-512',
                'sasl_plain_username': self.username,
                'sasl_plain_password': self.password,
                'ssl_check_hostname': True,
            })

            if self.ssl_ca_cert_path:
                config['ssl_cafile'] = self.ssl_ca_cert_path
            else:
                import ssl
                config['ssl_check_hostname'] = False
                config['ssl_context'] = ssl.create_default_context()
                config['ssl_context'].check_hostname = False
                config['ssl_context'].verify_mode = ssl.CERT_NONE

        consumer: Optional[KafkaConsumer] = None
        records: list[dict[str, Any]] = []

        try:
            consumer = KafkaConsumer(**config)
            partitions = consumer.partitions_for_topic(topic)

            if not partitions:
                logger.warning(f"Топик {topic} недоступен или пуст")
                return []

            topic_partitions = [TopicPartition(topic, partition) for partition in partitions]
            consumer.assign(topic_partitions)

            end_offsets = consumer.end_offsets(topic_partitions)
            partitions_with_data = set()

            for tp in topic_partitions:
                end_offset = end_offsets.get(tp, 0)
                start_offset = max(end_offset - limit, 0)
                consumer.seek(tp, start_offset)

                if start_offset < end_offset:
                    partitions_with_data.add(tp)

            if not partitions_with_data:
                logger.info("Новых событий регистрации нет")
                return []

            start_time = time.time()

            while partitions_with_data and (time.time() - start_time) < timeout_seconds:
                message_pack = consumer.poll(timeout_ms=500)

                if not message_pack:
                    continue

                for tp, messages in message_pack.items():
                    boundary = end_offsets.get(tp)

                    for message in messages:
                        if boundary is not None and message.offset >= boundary:
                            continue

                        try:
                            signup_event = SignUpEvent(**message.value)
                            records.append({
                                "timestamp": message.timestamp or 0,
                                "offset": message.offset,
                                "event": signup_event,
                            })
                        except Exception as e:
                            logger.error(f"Ошибка парсинга события регистрации: {e}")
                            continue

                        if boundary is not None and message.offset >= boundary - 1:
                            partitions_with_data.discard(tp)

                if len(records) >= limit:
                    break

            records.sort(key=lambda item: (item["timestamp"], item["offset"]))
            latest_events = [item["event"] for item in records[-limit:]]

            logger.info(f"Получено {len(latest_events)} регистраций из {topic}")
            return latest_events

        finally:
            if consumer:
                consumer.close()
    
    def _consume_messages(self):
        """Внутренний метод для потребления сообщений"""
        logger.info(f"Начато прослушивание топика {self.incoming_topic}")
        logger.info(f"Consumer group ID: {self.group_id}")
        logger.info(f"Подписка на топик: {self.consumer.subscription()}")
        
        partitions_assigned = False
        
        try:
            while self._running and self.consumer:
                try:
                    message_pack = self.consumer.poll(timeout_ms=1000)
                    
                    # Проверяем назначение партиций после первого poll
                    if not partitions_assigned:
                        assigned = self.consumer.assignment()
                        if assigned:
                            logger.info(f"✓ Назначенные партиции: {assigned}")
                            for tp in assigned:
                                position = self.consumer.position(tp)
                                logger.info(f"  Партиция {tp.partition}: текущая позиция = {position}")
                            partitions_assigned = True
                        else:
                            logger.debug("Ожидание назначения партиций...")
                    
                    if message_pack:
                        logger.debug(f"Получен пакет сообщений: {len(message_pack)} партиций")
                    
                    for topic_partition, messages in message_pack.items():
                        logger.debug(f"Обработка {len(messages)} сообщений из партиции {topic_partition.partition}")
                        
                        for message in messages:
                            try:
                                logger.debug(f"Сырые данные сообщения: {message.value}")
                                
                                # Валидация и создание Pydantic модели
                                kafka_message = KafkaIncomingMessage(**message.value)
                                
                                logger.info(
                                    f"✉️ Получено сообщение от абонента {kafka_message.from_abonent.phone}: "
                                    f"{kafka_message.text[:50] if kafka_message.text else 'Пустое сообщение'}..."
                                )
                                
                                # Вызов обработчика
                                if self._message_handler:
                                    logger.debug("Вызов обработчика сообщений...")
                                    self._call_handler(self._message_handler, kafka_message)
                                    logger.debug("Обработчик выполнен")
                                else:
                                    logger.warning("Обработчик сообщений не установлен!")
                                
                            except Exception as e:
                                logger.error(f"Ошибка обработки сообщения: {e}")
                                logger.error(f"Данные сообщения: {message.value}")
                                import traceback
                                logger.error(f"Traceback: {traceback.format_exc()}")
                    else:
                        # Если нет сообщений, логируем раз в 10 секунд
                        if not hasattr(self, '_last_no_msg_log') or time.time() - self._last_no_msg_log > 10:
                            logger.debug(f"Ожидание сообщений из {self.incoming_topic}...")
                            self._last_no_msg_log = time.time()
                                
                except Exception as e:
                    if self._running:  # Логируем только если не остановили принудительно
                        logger.error(f"Ошибка при получении сообщений: {e}")
                        import traceback
                        logger.error(f"Traceback: {traceback.format_exc()}")
                        time.sleep(1)  # Небольшая пауза перед повтором
                        
        except Exception as e:
            logger.error(f"Критическая ошибка в потоке потребления: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
        finally:
            logger.info("Завершен поток потребления сообщений")
    
    def _consume_signups(self):
        """Внутренний метод для потребления событий регистрации"""
        logger.info(f"Начато прослушивание топика {self.signups_topic}")
        logger.info(f"Consumer group ID: {self.group_id}")
        logger.info(f"Подписка на топик: {self.signups_consumer.subscription()}")
        
        partitions_assigned = False
        
        try:
            while self._signups_running and self.signups_consumer:
                try:
                    message_pack = self.signups_consumer.poll(timeout_ms=1000)
                    
                    # Проверяем назначение партиций после первого poll
                    if not partitions_assigned:
                        assigned = self.signups_consumer.assignment()
                        if assigned:
                            logger.info(f"✓ Назначенные партиции для SIGN_UPS: {assigned}")
                            for tp in assigned:
                                position = self.signups_consumer.position(tp)
                                logger.info(f"  Партиция {tp.partition}: текущая позиция = {position}")
                            partitions_assigned = True
                        else:
                            logger.debug("Ожидание назначения партиций для SIGN_UPS...")
                    
                    if message_pack:
                        logger.debug(f"Получен пакет событий регистрации: {len(message_pack)} партиций")
                    
                    for topic_partition, messages in message_pack.items():
                        logger.debug(f"Обработка {len(messages)} событий регистрации из партиции {topic_partition.partition}")
                        
                        for message in messages:
                            try:
                                logger.debug(f"Сырые данные события регистрации: {message.value}")
                                
                                # Валидация и создание Pydantic модели
                                signup_event = SignUpEvent(**message.value)
                                
                                logger.info(
                                    f"📝 Новая регистрация абонента {signup_event.abonent.phone} "
                                    f"(ID: {signup_event.abonent.id}) по адресу: "
                                    f"{signup_event.address.country.name}, {signup_event.address.city}, "
                                    f"ул.{signup_event.address.street.name}, д.{signup_event.address.house.number}"
                                )
                                
                                # Вызов обработчика
                                if self._signup_handler:
                                    logger.debug("Вызов обработчика событий регистрации...")
                                    self._call_handler(self._signup_handler, signup_event)
                                    logger.debug("Обработчик выполнен")
                                else:
                                    logger.warning("Обработчик событий регистрации не установлен!")
                                
                            except Exception as e:
                                logger.error(f"Ошибка обработки события регистрации: {e}")
                                logger.error(f"Данные события: {message.value}")
                                import traceback
                                logger.error(f"Traceback: {traceback.format_exc()}")
                    else:
                        # Если нет событий, логируем раз в 10 секунд
                        if not hasattr(self, '_last_no_signup_log') or time.time() - self._last_no_signup_log > 10:
                            logger.debug(f"Ожидание событий регистрации из {self.signups_topic}...")
                            self._last_no_signup_log = time.time()
                                
                except Exception as e:
                    if self._signups_running:
                        logger.error(f"Ошибка при получении событий регистрации: {e}")
                        import traceback
                        logger.error(f"Traceback: {traceback.format_exc()}")
                        time.sleep(1)
                        
        except Exception as e:
            logger.error(f"Критическая ошибка в потоке потребления регистраций: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
        finally:
            logger.info("Завершен поток потребления событий регистрации")
    
    def _consume_company_signups(self):
        """Внутренний метод для потребления событий регистрации компании"""
        logger.info(f"Начато прослушивание топика {self.company_signups_topic}")
        logger.info(f"Consumer group ID: {self.group_id}")
        logger.info(f"Подписка на топик: {self.company_signups_consumer.subscription()}")
        
        partitions_assigned = False
        
        try:
            while self._company_signups_running and self.company_signups_consumer:
                try:
                    message_pack = self.company_signups_consumer.poll(timeout_ms=1000)
                    
                    # Проверяем назначение партиций после первого poll
                    if not partitions_assigned:
                        assigned = self.company_signups_consumer.assignment()
                        if assigned:
                            logger.info(f"✓ Назначенные партиции для {self.company_signups_topic}: {assigned}")
                            for tp in assigned:
                                position = self.company_signups_consumer.position(tp)
                                logger.info(f"  Партиция {tp.partition}: текущая позиция = {position}")
                            partitions_assigned = True
                        else:
                            logger.debug(f"Ожидание назначения партиций для {self.company_signups_topic}...")
                    
                    if message_pack:
                        logger.debug(f"Получен пакет событий регистрации компании: {len(message_pack)} партиций")
                    
                    for topic_partition, messages in message_pack.items():
                        logger.debug(f"Обработка {len(messages)} событий регистрации компании из партиции {topic_partition.partition}")
                        
                        for message in messages:
                            try:
                                logger.debug(f"Сырые данные события регистрации компании: {message.value}")
                                
                                # Валидация и создание Pydantic модели
                                signup_event = SignUpEvent(**message.value)
                                
                                logger.info(
                                    f"📝 [Компания] Новая регистрация абонента {signup_event.abonent.phone} "
                                    f"(ID: {signup_event.abonent.id}) по адресу: "
                                    f"{signup_event.address.country.name}, {signup_event.address.city}, "
                                    f"ул.{signup_event.address.street.name}, д.{signup_event.address.house.number}"
                                )
                                
                                # Вызов обработчика
                                if self._company_signup_handler:
                                    logger.debug("Вызов обработчика событий регистрации компании...")
                                    self._call_handler(self._company_signup_handler, signup_event)
                                    logger.debug("Обработчик выполнен")
                                else:
                                    logger.warning("Обработчик событий регистрации компании не установлен!")
                                
                            except Exception as e:
                                logger.error(f"Ошибка обработки события регистрации компании: {e}")
                                logger.error(f"Данные события: {message.value}")
                                import traceback
                                logger.error(f"Traceback: {traceback.format_exc()}")
                    else:
                        # Если нет событий, логируем раз в 10 секунд
                        if not hasattr(self, '_last_no_company_signup_log') or time.time() - self._last_no_company_signup_log > 10:
                            logger.debug(f"Ожидание событий регистрации из {self.company_signups_topic}...")
                            self._last_no_company_signup_log = time.time()
                                
                except Exception as e:
                    if self._company_signups_running:
                        logger.error(f"Ошибка при получении событий регистрации компании: {e}")
                        import traceback
                        logger.error(f"Traceback: {traceback.format_exc()}")
                        time.sleep(1)
                        
        except Exception as e:
            logger.error(f"Критическая ошибка в потоке потребления регистраций компании: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
        finally:
            logger.info("Завершен поток потребления событий регистрации компании")
    
    def send_message(self, 
                     to_abonent_id: int, 
                     to_abonent_phone: int,
                     message: str,
                     from_abonent_id: Optional[int] = None,
                     from_abonent_phone: Optional[int] = None,
                     company_id: Optional[int] = None) -> bool:
        """
        Отправить сообщение через Kafka
        
        Args:
            to_abonent_id (int): ID получателя
            to_abonent_phone (int): Телефон получателя
            message (str): Текст сообщения
            from_abonent_id (int, optional): ID отправителя (для системных сообщений может быть None)
            from_abonent_phone (int, optional): Телефон отправителя
            company_id (int, optional): ID компании
            
        Returns:
            bool: True если сообщение отправлено успешно
            
        Example:
            >>> success = kafka_client.send_message(
            ...     to_abonent_id=1574870,
            ...     to_abonent_phone=79308312222,
            ...     message="Ответ на ваше сообщение",
            ...     from_abonent_id=0,  # Системное сообщение
            ...     from_abonent_phone=0
            ... )
            >>> print(success)
            True
        """
        if not self.producer:
            self.producer = self._create_producer()
        
        # Создание объектов получателя и отправителя
        to_abonent = KafkaAbonentInfo(
            id=to_abonent_id,
            phone=to_abonent_phone,
            company_id=company_id
        )
        
        from_abonent = None
        if from_abonent_id is not None and from_abonent_phone is not None:
            from_abonent = KafkaFromAbonent(
                id=from_abonent_id,
                phone=from_abonent_phone
            )
        
        # Создание сообщения
        kafka_message = KafkaOutgoingMessage(
            message=message,
            to_abonents=[to_abonent],
            from_abonent=from_abonent
        )
        
        try:
            # Отправка сообщения
            future = self.producer.send(
                self.outgoing_topic,
                value=kafka_message.model_dump(by_alias=True)
            )
            
            # Ждем подтверждения отправки
            record_metadata = future.get(timeout=10)
            
            logger.info(
                f"Сообщение отправлено в топик {record_metadata.topic}, "
                f"партиция {record_metadata.partition}, "
                f"offset {record_metadata.offset}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения: {e}")
            return False
    
    def send_message_to_multiple(self,
                                to_abonents: list[Dict[str, Any]],
                                message: str,
                                from_abonent_id: Optional[int] = None,
                                from_abonent_phone: Optional[int] = None) -> bool:
        """
        Отправить сообщение нескольким абонентам
        
        Args:
            to_abonents (list): Список получателей [{"id": int, "phone": int, "company_id": int}]
            message (str): Текст сообщения
            from_abonent_id (int, optional): ID отправителя
            from_abonent_phone (int, optional): Телефон отправителя
            
        Returns:
            bool: True если сообщение отправлено успешно
            
        Example:
            >>> recipients = [
            ...     {"id": 1574870, "phone": 79308312222, "company_id": 1292},
            ...     {"id": 1480844, "phone": 79061343111, "company_id": 1292}
            ... ]
            >>> success = kafka_client.send_message_to_multiple(
            ...     to_abonents=recipients,
            ...     message="Групповое сообщение"
            ... )
        """
        if not self.producer:
            self.producer = self._create_producer()
        
        # Создание списка получателей
        kafka_abonents = []
        for abonent in to_abonents:
            kafka_abonents.append(KafkaAbonentInfo(
                id=abonent["id"],
                phone=abonent["phone"],
                company_id=abonent.get("company_id")
            ))
        
        from_abonent = None
        if from_abonent_id is not None and from_abonent_phone is not None:
            from_abonent = KafkaFromAbonent(
                id=from_abonent_id,
                phone=from_abonent_phone
            )
        
        # Создание сообщения
        kafka_message = KafkaOutgoingMessage(
            message=message,
            to_abonents=kafka_abonents,
            from_abonent=from_abonent
        )
        
        try:
            # Отправка сообщения
            future = self.producer.send(
                self.outgoing_topic,
                value=kafka_message.model_dump(by_alias=True)
            )
            
            record_metadata = future.get(timeout=10)
            
            logger.info(
                f"Групповое сообщение отправлено {len(kafka_abonents)} получателям в топик {record_metadata.topic}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка отправки группового сообщения: {e}")
            return False
    
    def close(self):
        """
        Закрыть все соединения
        
        Example:
            >>> kafka_client.close()
        """
        self.stop_consuming()
        self.stop_signup_consuming()
        self.stop_company_signup_consuming()
        
        if self.producer:
            self.producer.close()
            self.producer = None
        
        logger.info("Kafka клиент закрыт")
    
    def __enter__(self):
        """Контекстный менеджер - вход"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Контекстный менеджер - выход"""
        self.close()

