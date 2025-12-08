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
    
    @validator('number', 'phone', pre=True)
    def convert_to_string(cls, v):
        """Преобразование int → str для совместимости с моделями, где phone как int"""
        if isinstance(v, int):
            return str(v)
        return v
    
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
    entrance_id: Optional[str] = Field(None, alias="entranceId")
    flat_number: str = Field(alias="flatNumber")
    virtual: bool = False
    
    @validator('entrance_id', 'flat_number', pre=True)
    def convert_to_string(cls, v):
        """Преобразование int → str для совместимости"""
        if v is None:
            return v
        if isinstance(v, int):
            return str(v)
        return v
    
    class Config:
        populate_by_name = True


class CreateFlatResponse(BaseModel):
    """Ответ при создании квартиры - полный объект с адресом и владельцем"""
    id: int
    address: Optional['Address'] = None
    owner: 'FlatOwner'
    virtual: bool


# Модели для услуг
class Service(BaseModel):
    """Услуга"""
    id: int
    name: str
    type: str


class CreateConnectionRequest(BaseModel):
    """Запрос на подключение услуги"""
    flat_id: int = Field(alias="flatId")
    account_id: Optional[int] = Field(None, alias="accountId")
    
    @validator('flat_id', pre=True)
    def convert_flat_id_to_int(cls, v):
        """Преобразование flat_id в int для API"""
        if isinstance(v, str):
            return int(v)
        return v
    
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
class SignUpCountry(BaseModel):
    """Информация о стране в событии регистрации"""
    short_name: str = Field(alias="shortName")
    name: str
    
    class Config:
        populate_by_name = True


class SignUpHouse(BaseModel):
    """Информация о доме в событии регистрации"""
    id: int
    number: str
    block: Optional[str] = None
    building: Optional[str] = None
    housing: Optional[str] = None


class SignUpStreet(BaseModel):
    """Информация об улице в событии регистрации"""
    id: int
    name: str
    code_fias: Optional[str] = Field(None, alias="codeFias")
    code_kladr: Optional[str] = Field(None, alias="codeKladr")
    universal_code: Optional[str] = Field(None, alias="universalCode")
    
    class Config:
        populate_by_name = True


class SignUpAddress(BaseModel):
    """Адрес в событии регистрации"""
    country: SignUpCountry
    city: str
    street: SignUpStreet
    house: SignUpHouse
    flat: Optional[int] = None


class SignUpAbonent(BaseModel):
    """Информация об абоненте в событии регистрации"""
    id: int
    phone: int


class SignUpApplication(BaseModel):
    """Информация о приложении через которое была регистрация"""
    id: int
    name: str
    provider: str
    company_id: Optional[int] = Field(None, alias="companyId")
    
    class Config:
        populate_by_name = True


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
    status: Optional[str] = None
    created_at: Optional[int] = Field(None, alias="createdAt")
    uid: Optional[str] = None
    services: Optional[List[ServiceInfo]] = Field(None, alias="services")
    
    class Config:
        populate_by_name = True


class UpdateSignUpRequest(BaseModel):
    """Запрос на обновление статуса заявки регистрации"""
    is_virtual: Optional[bool] = Field(None, alias="isVirtual")
    rejected_reason: Optional[str] = Field(None, alias="rejectedReason")
    status: Optional[str] = None
    
    @validator('status')
    def validate_status(cls, v):
        """Валидация статуса - должен быть одним из допустимых значений"""
        if v is not None:
            allowed_statuses = ['unprocessed', 'processed', 'connected', 'delegated', 'rejected']
            if v not in allowed_statuses:
                raise ValueError(f'Статус должен быть одним из: {", ".join(allowed_statuses)}')
        return v
    
    class Config:
        populate_by_name = True


# Модели для детальной информации об аккаунте
class Balance(BaseModel):
    """Информация о балансе аккаунта"""
    account_id: int = Field(alias="accountId")
    balance: float
    balance_date: int = Field(alias="balanceDate")
    currency: str
    is_payment_available: bool = Field(alias="isPaymentAvailable")
    recommended_payment_date: Optional[int] = Field(None, alias="recommendedPaymentDate")
    recommended_payment_sum: Optional[float] = Field(None, alias="recommendedPaymentSum")
    show_banner: bool = Field(alias="showBanner")
    
    class Config:
        populate_by_name = True


class Invoice(BaseModel):
    """Информация о счете"""
    amount: float
    currency: str
    date_begin: str = Field(alias="dateBegin")
    reminder_needed: bool = Field(alias="reminderNeeded")
    uid: str
    
    class Config:
        populate_by_name = True


class RecurringPayment(BaseModel):
    """Информация о рекуррентном платеже"""
    amount: float
    currency: str
    date: int
    reason: Optional[str] = None
    status: str  # NEW, PENDING, SUCCESS, FAILED
    
    class Config:
        populate_by_name = True


class Delegation(BaseModel):
    """Информация о делегировании доступа"""
    active: Optional[bool] = False
    id: int
    notification_success: Optional[bool] = Field(default=False, alias="notificationSuccess")
    from_abonent: Optional[str] = Field(None, alias="fromAbonent")
    to_abonent: Optional[str] = Field(None, alias="toAbonent")
    
    class Config:
        populate_by_name = True


class OwnerDetailed(BaseModel):
    """Детальная информация о владельце аккаунта"""
    id: int
    phone: Optional[int] = None
    resolved: Optional[bool] = True
    delegations: Optional[List[Delegation]] = Field(default_factory=list)
    fake_auth_on: Optional[bool] = Field(None, alias="fakeAuthOn")
    for_test: Optional[bool] = Field(None, alias="forTest")
    is_client: Optional[bool] = Field(None, alias="isClient")
    never_logged_in: Optional[bool] = Field(None, alias="neverLoggedIn")
    support_request_date: Optional[str] = Field(None, alias="supportRequestDate")
    uid: Optional[str] = None
    
    class Config:
        populate_by_name = True


class CompanyDetailed(BaseModel):
    """Детальная информация о компании"""
    id: int
    name: Optional[str] = None
    short_name: str = Field(alias="shortName")
    licensee_short: Optional[str] = Field(None, alias="licenseeShort")
    payment_link: Optional[str] = Field(None, alias="paymentLink")
    personal_account_link: Optional[str] = Field(None, alias="personalAccountLink")
    support_chat_enabled: Optional[bool] = Field(None, alias="supportChatEnabled")
    support_phone: Optional[str] = Field(None, alias="supportPhone")
    
    class Config:
        populate_by_name = True


class CityObject(BaseModel):
    """Информация о городе"""
    id: int
    name: str
    code_fias: Optional[str] = Field(None, alias="codeFias")
    type: Optional[str] = None
    type_full: Optional[str] = Field(None, alias="typeFull")
    
    class Config:
        populate_by_name = True


class CountryDetailed(BaseModel):
    """Детальная информация о стране"""
    name: str
    short_name: str = Field(alias="shortName")
    
    class Config:
        populate_by_name = True


class FlatRange(BaseModel):
    """Диапазон квартир"""
    id: int
    flat_start: int = Field(alias="flatStart")
    flat_end: int = Field(alias="flatEnd")
    
    class Config:
        populate_by_name = True


class EntranceDetailed(BaseModel):
    """Детальная информация о подъезде"""
    id: int
    number: str
    prefix: Optional[str] = None
    flat_start: int = Field(alias="flatStart")
    flat_end: int = Field(alias="flatEnd")
    additional_flat_ranges: List[FlatRange] = Field(default_factory=list, alias="additionalFlatRanges")
    
    class Config:
        populate_by_name = True


class HouseDetailed(BaseModel):
    """Детальная информация о доме"""
    id: int
    number: str
    block: Optional[str] = None
    building: Optional[str] = None
    housing: Optional[str] = None
    code_fias: Optional[str] = Field(None, alias="codeFias")
    type: Optional[str] = None
    type_full: Optional[str] = Field(None, alias="typeFull")
    geo_latitude: Optional[str] = Field(None, alias="geoLatitude")
    geo_longitude: Optional[str] = Field(None, alias="geoLongitude")
    geo_accuracy: Optional[str] = Field(None, alias="geoAccuracy")
    
    class Config:
        populate_by_name = True


class StreetDetailed(BaseModel):
    """Детальная информация об улице"""
    id: int
    name: str
    code_fias: Optional[str] = Field(None, alias="codeFias")
    code_kladr: Optional[str] = Field(None, alias="codeKladr")
    type: Optional[str] = None
    type_full: Optional[str] = Field(None, alias="typeFull")
    universal_code: Optional[str] = Field(None, alias="universalCode")
    
    class Config:
        populate_by_name = True


class AddressDetailed(BaseModel):
    """Детальная информация об адресе"""
    city: str
    flat: int
    country: CountryDetailed
    city_object: Optional[CityObject] = Field(None, alias="cityObject")
    entrance: EntranceDetailed
    house: HouseDetailed
    street: StreetDetailed
    
    class Config:
        populate_by_name = True


class Adapter(BaseModel):
    """Адаптер домофона"""
    rda_uid: str = Field(alias="rdaUid")
    intercom_index: Optional[str] = Field(None, alias="intercomIndex")
    camera_ids: List[int] = Field(default_factory=list, alias="cameraIds")
    
    class Config:
        populate_by_name = True


class FlatDetailed(BaseModel):
    """Детальная информация о квартире"""
    id: int
    account_id: Optional[int] = Field(None, alias="accountId")
    address: Optional[AddressDetailed] = None
    virtual: Optional[bool] = False
    blocked: Optional[bool] = False
    owner: OwnerDetailed
    adapters: Optional[List[Adapter]] = Field(default_factory=list)
    camera_id: Optional[int] = Field(None, alias="cameraId")
    hardware_intercom_id: Optional[int] = Field(None, alias="hardwareIntercomId")
    software_intercom_id: Optional[int] = Field(None, alias="softwareIntercomId")
    rda_uid: Optional[str] = Field(None, alias="rdaUid")
    translated: Optional[int] = None
    
    class Config:
        populate_by_name = True


class ServiceDetailed(BaseModel):
    """Детальная информация об услуге"""
    id: int
    name: str
    type: str
    company_id: Optional[int] = Field(None, alias="companyId")
    created_at: Optional[str] = Field(None, alias="createdAt")
    custom_name: Optional[str] = Field(None, alias="customName")
    delegation_tunings: Optional[DelegationTunings] = Field(None, alias="delegationTunings")
    accounts: Optional[List] = None
    
    class Config:
        populate_by_name = True


class ConnectionDetailed(BaseModel):
    """Детальная информация о подключении услуги"""
    id: int
    blocked: bool
    currency: Optional[str] = None
    tariff: Optional[float] = None
    delegation_tunings: Optional[DelegationTunings] = Field(None, alias="delegationTunings")
    flat: FlatDetailed
    service: ServiceDetailed
    
    class Config:
        populate_by_name = True


class AccountInfo(BaseModel):
    """Детальная информация об аккаунте"""
    id: int
    number: str
    blocked: bool
    billing_available: Optional[bool] = Field(None, alias="billingAvailable")
    is_company_recurring_enabled: Optional[bool] = Field(None, alias="isCompanyRecurringEnabled")
    terms_of_use_link: Optional[str] = Field(None, alias="termsOfUseLink")
    block_reason: Optional[str] = Field(None, alias="blockReason")
    paid_until: Optional[str] = Field(None, alias="paidUntil")
    balance: Optional[Balance] = None
    company: CompanyDetailed
    owner: OwnerDetailed
    connections: List[ConnectionDetailed] = Field(default_factory=list)
    invoice: Optional[Invoice] = None
    recurring_payment: Optional[RecurringPayment] = Field(None, alias="recurringPayment")
    
    class Config:
        populate_by_name = True


# Модели для получения подъездов с услугами
class Camera(BaseModel):
    """Камера видеонаблюдения"""
    id: int
    uri: str
    active: bool
    
    class Config:
        populate_by_name = True


class Location(BaseModel):
    """Локация домофона"""
    id: int
    name: str
    
    class Config:
        populate_by_name = True


class Intercom(BaseModel):
    """Домофон"""
    id: int
    index: str
    location: Optional[Location] = None
    
    class Config:
        populate_by_name = True


class RDA(BaseModel):
    """Устройство домофонной автоматики (RosDomofonAdapter)"""
    id: int
    uid: str
    active: bool
    intercoms: List[Intercom] = Field(default_factory=list)
    
    class Config:
        populate_by_name = True


class ServiceWithFullDetails(BaseModel):
    """Полная детальная информация об услуге с камерами, RDA и зависимыми услугами"""
    id: int
    name: str
    type: str
    company_id: Optional[int] = Field(None, alias="companyId")
    custom_name: Optional[str] = Field(None, alias="customName")
    autoconnection_enabled: Optional[bool] = Field(None, alias="autoconnectionEnabled")
    delegation_tunings: Optional[DelegationTunings] = Field(None, alias="delegationTunings")
    cameras: List[Camera] = Field(default_factory=list)
    rdas: List[RDA] = Field(default_factory=list)
    status: Optional[str] = None
    tariff: Optional[float] = None
    company: Optional[CompanyDetailed] = None
    dependant_services: Optional[List] = Field(None, alias="dependantServices")
    
    class Config:
        populate_by_name = True


class EntranceWithServices(BaseModel):
    """Подъезд с полным списком услуг"""
    id: int
    address_string: str = Field(alias="addressString")
    services: List[ServiceWithFullDetails] = Field(default_factory=list)
    
    class Config:
        populate_by_name = True


class EntrancesResponse(BaseModel):
    """Пагинированный ответ со списком подъездов"""
    content: List[EntranceWithServices]
    empty: bool
    first: bool
    last: bool
    number: int
    number_of_elements: int = Field(alias="numberOfElements")
    pageable: Optional[Pageable] = None
    size: int
    sort: Optional[Sort] = None
    total_elements: int = Field(alias="totalElements")
    total_pages: int = Field(alias="totalPages")
    
    class Config:
        populate_by_name = True


# Модели для получения квартир абонента
class FlatOwner(BaseModel):
    """Владелец квартиры (упрощенная модель)"""
    id: int


class AbonentFlat(BaseModel):
    """Квартира абонента"""
    id: int
    address: Address
    owner: FlatOwner
    virtual: bool


# Разрешение forward references для моделей с отложенными ссылками
CreateFlatResponse.model_rebuild()
