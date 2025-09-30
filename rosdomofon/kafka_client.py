"""
Клиент для работы с Kafka сообщениями РосДомофон
"""
import json
import threading
import time
from typing import Callable, Optional, Dict, Any
from kafka import KafkaConsumer, KafkaProducer
from loguru import logger

from models import KafkaIncomingMessage, KafkaOutgoingMessage, KafkaAbonentInfo, KafkaFromAbonent


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
        
        self.consumer: Optional[KafkaConsumer] = None
        self.producer: Optional[KafkaProducer] = None
        self._consumer_thread: Optional[threading.Thread] = None
        self._running = False
        self._message_handler: Optional[Callable] = None
        
        logger.info(f"Инициализация Kafka клиента для компании {company_short_name}")
        logger.info(f"Топик входящих сообщений: {self.incoming_topic}")
        logger.info(f"Топик исходящих сообщений: {self.outgoing_topic}")
        
        # Проверка доступных топиков
        self._check_available_topics()
    
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
                
        except Exception as e:
            logger.error(f"Ошибка при получении списка топиков: {e}")
    
    def set_message_handler(self, handler: Callable[[KafkaIncomingMessage], None]):
        """
        Установить обработчик входящих сообщений
        
        Args:
            handler (Callable): Функция для обработки входящих сообщений
            
        Example:
            >>> def handle_message(message: KafkaIncomingMessage):
            ...     print(f"Получено сообщение от {message.from_abonent.phone}: {message.message}")
            >>> 
            >>> kafka_client.set_message_handler(handle_message)
        """
        self._message_handler = handler
        logger.info("Установлен обработчик входящих сообщений")
    
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
                                    self._message_handler(kafka_message)
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

