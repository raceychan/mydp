import pika
import ssl

from pika.connection import ConnectionParameters
from typing import Any, Dict, List, Optional, Union, Set
from pydantic import BaseSettings, AnyHttpUrl, EmailStr, HttpUrl, AnyUrl, PostgresDsn, validator
from pandas.core.frame import DataFrame
from pandas.core.series import Series

from core.utils import build_url


class Settings(BaseSettings):
    class Config:
        env_file = 'core\\.env'
        env_file_encoding = 'utf-8'

    class DefaultValues:
        null = 0

    class DataBaseSettings:
        allowed_db = {'mysql', 'postgresql'}
        allowd_driver = {'pymysql', 'aiomysql'}
        default_async_engine = False

    EVENTS: Set[str] = {'instantiate', 'sql_update', 'data_update'}

    MYSQL_DB: str = 'mysql'
    MYSQL_DRIVER: str = 'pymysql'
    MYSQL_HOST: str
    MYSQL_PORT: str = '3306'
    MYSQL_USER: str
    MYSQL_PASSWORD: str

    DB_PARAMS_SCHEMA: Set[str] = {
        'db', 'driver', 'user', 'password', 'host', 'port'}

    SQLALCHEMY_DATABASE_URI: Optional[str] = ''

    @validator("SQLALCHEMY_DATABASE_URI", pre=True)
    def assemble_db_url(cls, v: Optional[str], values: Dict[str, Any], config, field) -> str:
        if v and isinstance(v, str):
            return v
        db_params_schema = values.get('DB_PARAMS_SCHEMA')
        db_params = {param: values.get(f'MYSQL_{param.upper()}')
                     for param in db_params_schema}
        return build_url(db_params=db_params, db_params_schema=db_params_schema)

    SQLALCHEMY_ASYNC_URL: Optional[str] = ''

    @validator("SQLALCHEMY_ASYNC_URL", pre=True)
    def assemble_aysnc_url(cls, v: Optional[str], values: Dict[str, Any], config, field) -> Any:
        if v and isinstance(v, str):
            return v
        db_params_schema = values.get('DB_PARAMS_SCHEMA')
        db_params = {param: values.get(f'MYSQL_{param.upper()}')
                     for param in db_params_schema}
        db_params['MYSQL_DRIVER'] = 'aiomysql'
        return build_url(db_params=db_params, db_params_schema=db_params_schema)

    RABBITMQ_DRIVER: str
    RABBITMQ_HOST: str
    RABBITMQ_PORT: str
    RABBITMQ_USER: str
    RABBITMQ_PASSWORD: str

    RABBITMQ_CONNECTION_PARAMETER: Optional[Any]

    @validator('RABBITMQ_CONNECTION_PARAMETER', pre=True)
    def assemble_mb_con(cls, v: Optional[str], values: Dict[str, Any], config, field) -> ConnectionParameters:
        if v and isinstance(v, str):
            return v
        RABBITMQ_USER = values.get('RABBITMQ_USER')
        RABBITMQ_PASSWORD = values.get('RABBITMQ_PASSWORD')
        RABBITMQ_HOST = values.get('RABBITMQ_HOST')
        RABBITMQ_PORT = values.get('RABBITMQ_PORT')
        credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        ssl_options = pika.SSLOptions(context)

        connection_params = pika.ConnectionParameters(
            port=RABBITMQ_PORT, host=RABBITMQ_HOST, credentials=credentials, ssl_options=ssl_options)
        return connection_params


settings = Settings()
defaults = Settings.DefaultValues()
