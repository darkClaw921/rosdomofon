"""
Пример использования Kafka интеграции с РосДомофон
"""
import time
from rosdomofon import RosDomofonAPI
from models import KafkaIncomingMessage


def handle_incoming_message(message: KafkaIncomingMessage):
    """
    Обработчик входящих сообщений из Kafka
    
    Args:
        message: Входящее сообщение от абонента
    """
    print(f"\n📨 Новое сообщение от абонента {message.from_abonent.phone}:")
    print(f"   Текст: {message.message}")
    print(f"   Канал: {message.channel}")
    print(f"   ID отправителя: {message.from_abonent.id}")
    
    # Пример автоответа через REST API
    # api.send_message_to_abonent(
    #     message.from_abonent.id,
    #     'support',
    #     f'Спасибо за сообщение! Получено: "{message.message}"'
    # )


def main():
    """Основная функция примера"""
    
    # Инициализация API с поддержкой Kafka
    api = RosDomofonAPI(
        username="your_username",
        password="your_password",
        kafka_bootstrap_servers="localhost:9092",  # Адрес Kafka брокера
        company_short_name="Your_Company_Name",    # Название компании для топиков
        kafka_group_id="rosdomofon_example_group"  # ID группы потребителей
    )
    
    try:
        # Авторизация
        print("🔐 Авторизация в API РосДомофон...")
        auth = api.authenticate()
        print(f"✅ Авторизация успешна! Токен получен.")
        
        # Установка обработчика Kafka сообщений
        print("📡 Настройка обработчика Kafka сообщений...")
        api.set_kafka_message_handler(handle_incoming_message)
        
        # Запуск потребления сообщений
        print("🚀 Запуск Kafka consumer...")
        api.start_kafka_consumer()
        print("✅ Kafka consumer запущен! Ожидание сообщений...")
        
        # Пример отправки сообщения через Kafka
        print("\n📤 Отправка тестового сообщения через Kafka...")
        success = api.send_kafka_message(
            to_abonent_id=1574870,
            to_abonent_phone=79308316689,
            message="Тестовое сообщение через Kafka",
            company_id=1292
        )
        
        if success:
            print("✅ Сообщение отправлено через Kafka!")
        else:
            print("❌ Ошибка отправки сообщения через Kafka")
        
        # Пример группового сообщения
        print("\n📤 Отправка группового сообщения...")
        recipients = [
            {"id": 1574870, "phone": 79308316689, "company_id": 1292},
            {"id": 1480844, "phone": 79061343115, "company_id": 1292}
        ]
        
        success = api.send_kafka_message_to_multiple(
            to_abonents=recipients,
            message="Групповое уведомление через Kafka"
        )
        
        if success:
            print("✅ Групповое сообщение отправлено!")
        else:
            print("❌ Ошибка отправки группового сообщения")
        
        # Работа в течение некоторого времени
        print("\n⏳ Ожидание входящих сообщений (30 секунд)...")
        print("   Отправьте сообщение через приложение РосДомофон для тестирования")
        
        time.sleep(30)
        
    except KeyboardInterrupt:
        print("\n⛔ Получен сигнал остановки...")
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        
    finally:
        # Остановка Kafka consumer
        print("🛑 Остановка Kafka consumer...")
        api.stop_kafka_consumer()
        
        # Закрытие соединений
        print("🔒 Закрытие соединений...")
        api.close()
        
        print("✅ Завершение работы")


if __name__ == "__main__":
    print("🔄 Запуск примера Kafka интеграции с РосДомофон")
    print("=" * 50)
    main()
