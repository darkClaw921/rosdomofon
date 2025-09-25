from rosdomofon import RosDomofonAPI
from dotenv import load_dotenv
import os
load_dotenv()
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")

def main():
    print("Hello from rosdomofon-bitrix24!")
    api = RosDomofonAPI(username=USERNAME, password=PASSWORD)
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
