from typing import Any, Dict, List, Optional, Union
from pydantic import AnyHttpUrl, BaseSettings, EmailStr, HttpUrl, PostgresDsn, validator
from pandas.core.frame import DataFrame
from pandas.core.series import Series


class Settings(BaseSettings):
    PRE_FIX: List[str] = ['N', 'NN', 'PR']
    SUR_FIX: List[str] = ['-WP', '-a', '-b', '-c']
    CNT: List[str] = ['-WP']
    COUNTRIES: List[str] = ['官网', 'CA', 'DE', 'UK', 'JP', 'AU']
    COUNTRY_ORI_SUB: Dict[str, str] = {
        country: country for country in COUNTRIES}
    COUNTRY_MEG_SUB: Dict[str, str] = {
        'IT': 'DE', 'FR': 'DE', 'ES': 'DE', 'US01': 'US', 'US02': '官网'}
    COUNTRY_SUB: Dict[str, str] = {**COUNTRY_MEG_SUB, **COUNTRY_ORI_SUB}
    DB_PARAMS: Dict[str, str] = {key: '' for key in [
        'db', 'db_driver', 'db_user', 'db_password', 'db_host', 'db_schema']}

    EVENTS = ['instantiate', 'sql_update', 'data_update']


settings = Settings()
