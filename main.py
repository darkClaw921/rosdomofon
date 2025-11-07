from rosdomofon import RosDomofonAPI
from rosdomofon.models import SignUpEvent
from dotenv import load_dotenv
import os
from pprint import pprint
import time
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
    print("Hello from rosdomofon-bitrix24!")
    api = RosDomofonAPI(
        username=USERNAME, 
        password=PASSWORD, 
        # kafka_bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS, 
        # kafka_username=KAFKA_USERNAME, 
        # kafka_password=KAFKA_PASSWORD, 
        # kafka_group_id=KAFKA_GROUP_ID,
        # kafka_ssl_ca_cert_path=KAFKA_SSL_CA_CERT_PATH,
        # company_short_name=COMPANY_SHORT_NAME
        )
    api.authenticate()
    # find_entrance = api.find_entrance_by_address_and_flat("Чебоксары", "Филиппа Лукина", "5", 65)
    # pprint(find_entrance)
    api.update_signup(1526294, status='connected')
    # for entrance in entrances.content:
    #     pprint(entrance.__dict__)
    # services = api.get_all_services()
    # pprint(services)
    # api.set_company_signup_handler(handle_company_signup)
    # api.start_company_signup_consumer()
    # account = api.get_account_by_phone(79308312222)
    # print(account)
    # abonent_id=account.owner.id
    # account_id=account.id

    #получаем услуги абонента
    # services = api.get_account_connections(account_id)
    # print(services)
    # connection_id=services[0].id
    # print(connection_id)

    # api.unblock_connection(connection_id)
    # service_connections = api.get_service_connections(connection_id)
    # print(service_connections)

    # time.sleep(100)
    # print("🛑 Остановка Kafka consumer регистраций компании...")
    # api.stop_company_signup_consumer()
    # print("🔒 Закрытие соединений...")
    # api.close()
    # messages = api.get_abonent_messages(abonent_id, channel='support', page=0, size=10)
    # print(messages)

    # отправляем сообщение
    # api.send_message_to_abonent(abonent_id, 'support', f'вы написали {messages.content[0].message}')
    # for account in accounts:
    #     print(f"ID: {account.id}")
    #     print(f"Телефон: {account.owner.phone}")
    #     print(f"Заблокирован: {account.blocked}")
    #     print(f"Номер счета: {account.number or 'Не указан'}")

if __name__ == "__main__":
    main()
