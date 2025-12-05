import asyncio
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
# print(f'{api.kafka_client=}')
# Чебоксары, Академика РАН Х.М.Миначева, 19, кв.143



async def old_algorithm():
    accounts=api.get_accounts()
    prepareProducts={}
    for account in accounts:
        phone=account.owner.phone
        # phone=normalize_phone(phone)
        account = api.get_account_by_phone(int(phone))
        connections = api.get_account_connections(account.id)
        for connection in connections:
            fields = {
                "PRICE": connection.tariff,
                "CURRENCY_ID": "RUB",
                "ADDRESS":connection.service.name,
                "ID_SERVICE_ROSDOMOFON":connection.service.id,
            }
            # asyncio.run(create_product(connection.service.custom_name, fields))
            prepareProducts[connection.service.custom_name]=fields
            # logger.info(f"Создан товар {connection.service.custom_name}")

    # pprint(prepareProducts)
    return prepareProducts

async def new_algorithm():
    entrances = api.get_entrances(all=True)
    prepareProducts={}
    for entrance in entrances.content:
        for service in entrance.services:
            fields = {
                "PRICE": service.tariff,
                "CURRENCY_ID": "RUB",
                "ADDRESS":service.name,
                "ID_SERVICE_ROSDOMOFON":service.id,
            }
            prepareProducts[service.custom_name]=fields
    # pprint(prepareProducts)
    return prepareProducts

async def main():
    old_prepareProducts = await old_algorithm()
    new_prepareProducts = await new_algorithm()
    pprint(old_prepareProducts)
    pprint(new_prepareProducts)
    if old_prepareProducts == new_prepareProducts:
        print("Products are the same")
    else:
        for key, value in old_prepareProducts.items():
            if key not in new_prepareProducts:
                print(f"Product {key} is missing in new algorithm")
            else:
                if value != new_prepareProducts[key]:
                    print(f"Product {key} is different in new algorithm")
                    print(f"Old value: {value}")
                    print(f"New value: {new_prepareProducts[key]}")
                    print("--------------------------------")
        for key, value in new_prepareProducts.items():
            if key not in old_prepareProducts:
                print(f"Product {key} is missing in old algorithm")
            else:
                if value != old_prepareProducts[key]:
                    print(f"Product {key} is different in old algorithm")
                    print(f"Old value: {old_prepareProducts[key]}")
                    print(f"New value: {value}")
                    print("--------------------------------")

if __name__ == "__main__":
    asyncio.run(main())
    # a=asyncio.run(new_algorithm())
    # pprint(a)