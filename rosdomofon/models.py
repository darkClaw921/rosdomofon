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
    licensee_short: str = Field(alias="licenseeShort")
    
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


class Connection(BaseModel):
    """Подключение"""
    id: int
    # Дополнительные поля будут добавлены по мере необходимости


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


class KafkaIncomingMessage(BaseModel):
    """Входящее сообщение из Kafka (MESSAGES_IN топик)"""
    channel: str
    delivery_method: str = Field(alias="deliveryMethod")
    from_abonent: KafkaFromAbonent = Field(alias="fromAbonent")
    message: str
    to_abonents: List[KafkaAbonentInfo] = Field(alias="toAbonents")
    
    class Config:
        populate_by_name = True


class KafkaOutgoingMessage(BaseModel):
    """Исходящее сообщение для Kafka (MESSAGES_OUT топик)"""
    channel: str = "support"
    delivery_method: str = Field(default="PUSH", alias="deliveryMethod")
    from_abonent: Optional[KafkaFromAbonent] = Field(None, alias="fromAbonent")
    message: str
    to_abonents: List[KafkaAbonentInfo] = Field(alias="toAbonents")
    
    class Config:
        populate_by_name = True
