"""
Pydantic модели для работы с API РосДомофон
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, validator


# Модели для авторизации
class AuthResponse(BaseModel):
    """Ответ при авторизации"""
    access_token: str
    token_type: str
    expires_in: int
    scope: str
    
    
# Модели для абонентов
class Owner(BaseModel):
    """Владелец аккаунта"""
    id: int
    never_logged_in: Optional[bool] = None
    phone: int
    resolved: bool = True


class Company(BaseModel):
    """Компания"""
    id: int
    short_name: str = Field(alias="shortName")
    licensee_short: Optional[str] = Field(None, alias="licenseeShort")
    
    class Config:
        populate_by_name = True


class Account(BaseModel):
    """Аккаунт абонента"""
    id: int
    billing_available: Optional[bool] = Field(None, alias="billingAvailable")
    number: Optional[str] = None
    terms_of_use_link: Optional[str] = Field(None, alias="termsOfUseLink")
    block_reason: Optional[str] = Field(None, alias="blockReason")
    owner: Owner # abonent
    company: Company
    blocked: bool
    is_company_recurring_enabled: bool = Field(alias="isCompanyRecurringEnabled")
    
    class Config:
        populate_by_name = True


class CreateAccountRequest(BaseModel):
    """Запрос на создание аккаунта"""
    number: str
    phone: str
    
    @validator('phone')
    def validate_phone(cls, v):
        """Валидация телефона - должен быть в формате 79131234567"""
        if not v.isdigit() or len(v) != 11 or not v.startswith('7'):
            raise ValueError('Номер телефона должен быть в формате 79131234567')
        return v


class CreateAccountResponse(BaseModel):
    """Ответ при создании аккаунта"""
    id: int
    owner: Owner


# Модели для квартир
class CreateFlatRequest(BaseModel):
    """Запрос на создание квартиры"""
    abonent_id: Optional[int] = Field(None, alias="abonentId")
    entrance_id: str = Field(alias="entranceId")
    flat_number: str = Field(alias="flatNumber")
    virtual: bool = False
    
    class Config:
        populate_by_name = True


class CreateFlatResponse(BaseModel):
    """Ответ при создании квартиры"""
    id: str


# Модели для услуг
class Service(BaseModel):
    """Услуга"""
    id: int
    name: str
    type: str


class CreateConnectionRequest(BaseModel):
    """Запрос на подключение услуги"""
    flat_id: str = Field(alias="flatId")
    account_id: Optional[int] = Field(None, alias="accountId")
    
    class Config:
        populate_by_name = True


class CreateConnectionResponse(BaseModel):
    """Ответ при подключении услуги"""
    id: int


class Country(BaseModel):
    """Страна"""
    name: str
    short_name: str = Field(alias="shortName")
    
    class Config:
        populate_by_name = True


class Entrance(BaseModel):
    """Подъезд"""
    id: int
    number: str
    flat_start: int = Field(alias="flatStart")
    flat_end: int = Field(alias="flatEnd")
    additional_flat_ranges: List = Field(default_factory=list, alias="additionalFlatRanges")
    
    class Config:
        populate_by_name = True


class House(BaseModel):
    """Дом"""
    id: int
    number: str


class Street(BaseModel):
    """Улица"""
    id: int
    name: str
    code_fias: str = Field(alias="codeFias")
    code_kladr: str = Field(alias="codeKladr")
    
    class Config:
        populate_by_name = True


class Address(BaseModel):
    """Адрес"""
    city: str
    country: Country
    entrance: Entrance
    flat: int
    house: House
    street: Street


class Flat(BaseModel):
    """Квартира"""
    id: int
    account_id: int = Field(alias="accountId")
    address: Address
    virtual: bool
    
    class Config:
        populate_by_name = True


class DelegationTunings(BaseModel):
    """Настройки делегирования"""
    limit: Optional[int] = None


class ServiceInfo(BaseModel):
    """Информация об услуге"""
    id: int
    company_id: Optional[int] = Field(None, alias="companyId")
    created_at: int = Field(alias="createdAt")
    custom_name: Optional[str] = Field(None, alias="customName")
    delegation_tunings: DelegationTunings = Field(alias="delegationTunings")
    name: str
    type: str
    
    class Config:
        populate_by_name = True


class Connection(BaseModel):
    """Подключение услуги к квартире"""
    id: int
    account: Account
    blocked: bool
    currency: Optional[str] = None
    delegation_tunings: DelegationTunings = Field(alias="delegationTunings")
    flat: Flat
    service: ServiceInfo
    tariff: Optional[float] = None
    
    class Config:
        populate_by_name = True


# Модели для сообщений
class AbonentInfo(BaseModel):
    """Информация об абоненте в сообщении"""
    id: int
    phone: int


class Message(BaseModel):
    """Сообщение"""
    abonent: AbonentInfo
    channel: str
    id: int
    incoming: bool
    message: str
    message_date: datetime = Field(alias="messageDate")
    
    class Config:
        populate_by_name = True


class Pageable(BaseModel):
    """Информация о пагинации"""
    offset: int
    page_number: int = Field(alias="pageNumber")
    page_size: int = Field(alias="pageSize")
    paged: bool
    unpaged: bool
    
    class Config:
        populate_by_name = True


class Sort(BaseModel):
    """Информация о сортировке"""
    sorted: bool
    unsorted: bool


class MessagesResponse(BaseModel):
    """Ответ при получении сообщений"""
    content: List[Message]
    first: bool
    last: bool
    number: int
    number_of_elements: int = Field(alias="numberOfElements")
    pageable: Pageable
    size: int
    sort: Sort
    total_elements: int = Field(alias="totalElements")
    total_pages: int = Field(alias="totalPages")
    
    class Config:
        populate_by_name = True


class SendMessageRequest(BaseModel):
    """Запрос на отправку сообщения"""
    to_abonents: List[AbonentInfo] = Field(alias="toAbonents")
    channel: str
    message: str
    delivery_method: str = Field(default="push", alias="deliveryMethod")
    broadcast: Optional[bool] = False
    
    class Config:
        populate_by_name = True


# Модели для Kafka сообщений
class KafkaAbonentInfo(BaseModel):
    """Информация об абоненте в Kafka сообщении"""
    company_id: Optional[int] = Field(None, alias="companyId")
    id: int
    phone: int
    
    class Config:
        populate_by_name = True


class KafkaFromAbonent(BaseModel):
    """Отправитель сообщения в Kafka"""
    id: int
    phone: int
    company_id: Optional[int] = Field(None, alias="companyId")
    restriction_push_token_ids: Optional[List] = Field(default_factory=list, alias="restrictionPushTokenIds")
    
    class Config:
        populate_by_name = True


class LocalizedPush(BaseModel):
    """Локализованное push-уведомление"""
    message: Optional[str] = None
    message_key: Optional[str] = Field(None, alias="messageKey")
    message_args: Optional[List] = Field(None, alias="messageArgs")
    
    class Config:
        populate_by_name = True


class KafkaIncomingMessage(BaseModel):
    """Входящее сообщение из Kafka (MESSAGES_IN топик)"""
    channel: str
    delivery_method: Optional[str] = Field(None, alias="deliveryMethod")
    from_abonent: KafkaFromAbonent = Field(alias="fromAbonent")
    message: Optional[str] = None
    to_abonents: Optional[List[KafkaAbonentInfo]] = Field(None, alias="toAbonents")
    broadcast: Optional[bool] = False
    sms_message: Optional[str] = Field(None, alias="smsMessage")
    message_code: Optional[str] = Field(None, alias="messageCode")
    chat_id: Optional[str] = Field(None, alias="chatId")
    wait_response: Optional[bool] = Field(None, alias="waitResponse")
    properties: Optional[dict] = None
    providers: Optional[List] = None
    app_names: Optional[List] = Field(None, alias="appNames")
    localized_push: Optional[LocalizedPush] = Field(None, alias="localizedPush")
    localized_sms: Optional[dict] = Field(None, alias="localizedSms")
    image_url: Optional[str] = Field(None, alias="imageUrl")
    
    class Config:
        populate_by_name = True
    
    @property
    def text(self) -> str:
        """Получить текст сообщения из message или localizedPush.message"""
        if self.message:
            return self.message
        if self.localized_push and self.localized_push.message:
            return self.localized_push.message
        return ""


class KafkaOutgoingMessage(BaseModel):
    """Исходящее сообщение для Kafka (MESSAGES_OUT топик)"""
    channel: str = "support"
    delivery_method: str = Field(default="PUSH", alias="deliveryMethod")
    from_abonent: Optional[KafkaFromAbonent] = Field(None, alias="fromAbonent")
    message: Optional[str] = None
    to_abonents: List[KafkaAbonentInfo] = Field(alias="toAbonents")
    localized_push: Optional[LocalizedPush] = Field(None, alias="localizedPush")
    
    class Config:
        populate_by_name = True


# Модели для SIGN_UPS_ALL топика
class SignUpHouse(BaseModel):
    """Информация о доме в событии регистрации"""
    block: Optional[str] = None
    building: Optional[str] = None
    housing: Optional[str] = None
    number: str


class SignUpStreet(BaseModel):
    """Информация об улице в событии регистрации"""
    code_fias: Optional[str] = Field(None, alias="codeFias")
    code_kladr: Optional[str] = Field(None, alias="codeKladr")
    name: str
    
    class Config:
        populate_by_name = True


class SignUpAddress(BaseModel):
    """Адрес в событии регистрации"""
    city: str
    flat: int
    house: SignUpHouse
    street: SignUpStreet


class SignUpAbonent(BaseModel):
    """Информация об абоненте в событии регистрации"""
    id: int
    phone: int


class SignUpApplication(BaseModel):
    """Информация о приложении через которое была регистрация"""
    id: int
    name: str
    provider: str


class SignUpEvent(BaseModel):
    """Событие регистрации абонента (SIGN_UPS_ALL топик)"""
    id: int
    abonent: SignUpAbonent
    address: SignUpAddress
    application: SignUpApplication
    time_zone: str = Field(alias="timeZone")
    virtual: bool
    offer_signed: bool = Field(alias="offerSigned")
    contract_number: Optional[str] = Field(None, alias="contractNumber")
    
    class Config:
        populate_by_name = True
