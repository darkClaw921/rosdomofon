from rosdomofon import RosDomofonAPI
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
print(f'{KAFKA_SSL_CA_CERT_PATH=}')
def main():
    print("Hello from rosdomofon-bitrix24!")
    api = RosDomofonAPI(
        username=USERNAME, 
        password=PASSWORD, 
        kafka_bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS, 
        kafka_username=KAFKA_USERNAME, 
        kafka_password=KAFKA_PASSWORD, 
        kafka_group_id=KAFKA_GROUP_ID,
        kafka_ssl_ca_cert_path=KAFKA_SSL_CA_CERT_PATH
        )
    api.authenticate()
    
    account = api.get_account_by_phone(79308312222)
    print(account)
    abonent_id=account.owner.id
    account_id=account.id

    #получаем услуги абонента
    services = api.get_account_connections(account_id)
    print(services)
    connection_id=services[0].id


    api.unblock_connection(connection_id)
    # service_connections = api.get_service_connections(connection_id)
    # print(service_connections)



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
