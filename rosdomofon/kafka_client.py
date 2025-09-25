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
                 group_id: Optional[str] = None):
        """
        Инициализация Kafka клиента
        
        Args:
            bootstrap_servers (str): Адрес Kafka брокеров
            company_short_name (str): Короткое название компании для формирования топиков
            group_id (str, optional): ID группы потребителей
            
        Example:
            >>> kafka_client = RosDomofonKafkaClient(
            ...     bootstrap_servers="kafka.example.com:9092",
            ...     company_short_name="Video_SB",
            ...     group_id="rosdomofon_group"
            ... )
        """
        self.bootstrap_servers = bootstrap_servers
        self.company_short_name = company_short_name
        self.group_id = group_id or f"rosdomofon_{company_short_name}_group"
        
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
    
    def _create_consumer(self) -> KafkaConsumer:
        """Создать Kafka consumer"""
        return KafkaConsumer(
            self.incoming_topic,
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            auto_offset_reset='latest',
            enable_auto_commit=True,
            value_deserializer=lambda x: json.loads(x.decode('utf-8')),
            consumer_timeout_ms=1000
        )
    
    def _create_producer(self) -> KafkaProducer:
        """Создать Kafka producer"""
        return KafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda x: json.dumps(x, ensure_ascii=False).encode('utf-8'),
            acks='all',
            retries=3
        )
    
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
        
        try:
            while self._running and self.consumer:
                try:
                    message_pack = self.consumer.poll(timeout_ms=1000)
                    
                    for topic_partition, messages in message_pack.items():
                        for message in messages:
                            try:
                                # Валидация и создание Pydantic модели
                                kafka_message = KafkaIncomingMessage(**message.value)
                                
                                logger.info(
                                    f"Получено сообщение от абонента {kafka_message.from_abonent.phone}: "
                                    f"{kafka_message.message[:50]}..."
                                )
                                
                                # Вызов обработчика
                                if self._message_handler:
                                    self._message_handler(kafka_message)
                                
                            except Exception as e:
                                logger.error(f"Ошибка обработки сообщения: {e}")
                                logger.error(f"Данные сообщения: {message.value}")
                                
                except Exception as e:
                    if self._running:  # Логируем только если не остановили принудительно
                        logger.error(f"Ошибка при получении сообщений: {e}")
                        time.sleep(1)  # Небольшая пауза перед повтором
                        
        except Exception as e:
            logger.error(f"Критическая ошибка в потоке потребления: {e}")
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
            ...     to_abonent_phone=79308316689,
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
                value=kafka_message.dict(by_alias=True)
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
            ...     {"id": 1574870, "phone": 79308316689, "company_id": 1292},
            ...     {"id": 1480844, "phone": 79061343115, "company_id": 1292}
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
                value=kafka_message.dict(by_alias=True)
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
