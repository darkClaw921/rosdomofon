"""
Пример использования Kafka интеграции с РосДомофон
"""
import time
from .rosdomofon import RosDomofonAPI
from .models import KafkaIncomingMessage, SignUpEvent
from dotenv import load_dotenv
import os
load_dotenv()
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
KAFKA_USERNAME = os.getenv("KAFKA_USERNAME")
KAFKA_PASSWORD = os.getenv("KAFKA_PASSWORD")
KAFKA_GROUP_ID = os.getenv("KAFKA_GROUP_ID")
KAFKA_SSL_CA_CERT_PATH = os.getenv("KAFKA_SSL_CA_CERT_PATH")
COMPANY_SHORT_NAME = os.getenv("COMPANY_SHORT_NAME")
print(f'{KAFKA_SSL_CA_CERT_PATH=}')



def handle_incoming_message(message: KafkaIncomingMessage):
    """
    Обработчик входящих сообщений из Kafka
    
    Args:
        message: Входящее сообщение от абонента
    """
    print(f"\n📨 Новое сообщение от абонента {message.from_abonent.phone}:")
    print(f"   Текст: {message.text}")
    print(f"   Канал: {message.channel}")
    print(f"   ID отправителя: {message.from_abonent.id}")
    print(f"   Company ID: {message.from_abonent.company_id}")
    
    # Пример автоответа через REST API
    # api.send_message_to_abonent(
    #     message.from_abonent.id,
    #     'support',
    #     f'Спасибо за сообщение! Получено: "{message.message}"'
    # )


def handle_signup(signup: SignUpEvent):
    """
    Обработчик событий регистрации из Kafka (общий топик SIGN_UPS_ALL)
    
    Args:
        signup: Событие регистрации нового абонента
    """
    print(f"\n📝 [Общий топик] Новая регистрация абонента:")
    print(f"   ID: {signup.abonent.id}")
    print(f"   Телефон: {signup.abonent.phone}")
    print(f"   Страна: {signup.address.country.name} ({signup.address.country.short_name})")
    print(f"   Адрес: {signup.address.city}, ул.{signup.address.street.name}, д.{signup.address.house.number}")
    print(f"   Приложение: {signup.application.name} ({signup.application.provider})")
    print(f"   Виртуальная трубка: {signup.virtual}")
    print(f"   Оферта подписана: {signup.offer_signed}")
    print(f"   Номер договора: {signup.contract_number or 'не указан'}")
    print(f"   Статус: {signup.status}")
    
    # Пример отправки приветственного сообщения через REST API
    # api.send_message_to_abonent(
    #     signup.abonent.id,
    #     'support',
    #     'Добро пожаловать в систему РосДомофон!'
    # )


def handle_company_signup(signup: SignUpEvent):
    """
    Обработчик событий регистрации из Kafka (топик компании SIGN_UPS_<company_short_name>)
    
    Args:
        signup: Событие регистрации нового абонента в компании
    """
    print(f"\n📝 [Топик компании] Новая регистрация абонента:")
    print(f"   ID: {signup.abonent.id}")
    print(f"   Телефон: {signup.abonent.phone}")
    print(f"   Страна: {signup.address.country.name} ({signup.address.country.short_name})")
    print(f"   Адрес: {signup.address.city}, ул.{signup.address.street.name}, д.{signup.address.house.number}")
    print(f"   Приложение: {signup.application.name} ({signup.application.provider})")
    print(f"   Виртуальная трубка: {signup.virtual}")
    print(f"   Оферта подписана: {signup.offer_signed}")
    print(f"   Номер договора: {signup.contract_number or 'не указан'}")
    print(f"   Статус: {signup.status}")
    
    # Пример отправки приветственного сообщения через REST API
    # api.send_message_to_abonent(
    #     signup.abonent.id,
    #     'support',
    #     'Добро пожаловать в нашу компанию!'
    # )


def main():
    """Основная функция примера"""
    
    # Инициализация API с поддержкой Kafka
    api = RosDomofonAPI(
            username=USERNAME,
        password=PASSWORD,
        kafka_bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,  # Адрес Kafka брокера
        company_short_name=COMPANY_SHORT_NAME,    # Название компании для топиков
        kafka_group_id=KAFKA_GROUP_ID,  # ID группы потребителей
        kafka_username=KAFKA_USERNAME,
        kafka_password=KAFKA_PASSWORD,
        kafka_ssl_ca_cert_path=KAFKA_SSL_CA_CERT_PATH

    )
    
    try:
        # Авторизация
        print("🔐 Авторизация в API РосДомофон...")
        auth = api.authenticate()
        print(f"✅ Авторизация успешна! Токен получен.")
        
        # Установка обработчика Kafka сообщений
        print("📡 Настройка обработчика Kafka сообщений...")
        api.set_kafka_message_handler(handle_incoming_message)
        
        # Установка обработчика регистраций (общий топик)
        print("📡 Настройка обработчика регистраций (общий топик SIGN_UPS_ALL)...")
        api.set_signup_handler(handle_signup)
        
        # Установка обработчика регистраций компании
        print("📡 Настройка обработчика регистраций компании (SIGN_UPS_<company>)...")
        api.set_company_signup_handler(handle_company_signup)
        
        # Запуск потребления сообщений
        print("🚀 Запуск Kafka consumer...")
        api.start_kafka_consumer()
        print("✅ Kafka consumer запущен! Ожидание сообщений...")
        
        # Запуск потребления регистраций (общий топик)
        print("🚀 Запуск Kafka consumer для регистраций (общий топик)...")
        api.start_signup_consumer()
        print("✅ Kafka consumer регистраций запущен!")
        
        # Запуск потребления регистраций компании
        print("🚀 Запуск Kafka consumer для регистраций компании...")
        api.start_company_signup_consumer()
        print("✅ Kafka consumer регистраций компании запущен!")
        
        # Пример отправки сообщения через Kafka
        # print("\n📤 Отправка тестового сообщения через Kafka...")
        # success = api.send_kafka_message(
        #     to_abonent_id=1574870,
        #     to_abonent_phone=79308312222,
        #     message="Тестовое сообщение через Kafka",
        #     # company_id=1292
        # )
        
        # if success:
        #     print("✅ Сообщение отправлено через Kafka!")
        # else:
        #     print("❌ Ошибка отправки сообщения через Kafka")
        
        # Пример группового сообщения
        # print("\n📤 Отправка группового сообщения...")
        # recipients = [
        #     {"id": 1574870, "phone": 79308312222, "company_id": 1292}
        #     # {"id": 1480844, "phone": 79061343115, "company_id": 1292}
        # ]
        
        # success = api.send_kafka_message_to_multiple(
        #     to_abonents=recipients,
        #     message="Групповое уведомление через Kafka"
        # )
        
        # if success:
        #     print("✅ Групповое сообщение отправлено!")
        # else:
        #     print("❌ Ошибка отправки группового сообщения")
        
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
        
        # Остановка Kafka consumer для регистраций (общий топик)
        print("🛑 Остановка Kafka consumer регистраций (общий топик)...")
        api.stop_signup_consumer()
        
        # Остановка Kafka consumer для регистраций компании
        print("🛑 Остановка Kafka consumer регистраций компании...")
        api.stop_company_signup_consumer()
        
        # Закрытие соединений
        print("🔒 Закрытие соединений...")
        api.close()
        
        print("✅ Завершение работы")


if __name__ == "__main__":
    print("🔄 Запуск примера Kafka интеграции с РосДомофон")
    print("=" * 50)
    main()

