import os

from typing import Dict, List, Union, Optional, Any
from pandas.core.frame import DataFrame
from pandas.core.series import Series

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.engine.base import Engine
from sqlalchemy.ext.asyncio.engine import AsyncEngine
from core.config import settings


DIRNAME = os.path.dirname(__file__)
ENVPATH = os.path.join(DIRNAME, '.env')


class DataBase:
    def __init__(self):
        self._async_engine = create_async_engine(
            settings.SQLALCHEMY_ASYNC_URL, pool_pre_ping=True)
        self._engine = create_engine(
            settings.SQLALCHEMY_DATABASE_URI, pool_pre_ping=True)

    @property
    def async_engine(self) -> AsyncEngine:
        if not self._async_engine:
            self._async_engine = create_async_engine(
                settings.SQLALCHEMY_ASYNC_URL
            )
        return self._async_engine

    @property
    def engine(self) -> Engine:
        if not self._async_engine:
            self.async_engine

        if not self._engine:
            self._engine = create_engine(
                settings.SQLALCHEMY_DATABASE_URI
            )
        return self._engine

    @property
    def con(self) -> Any:
        con = self._engine.begin()
        return con

    def read_sql(self, sql: str) -> DataFrame:
        with self.con as conn:
            data = conn.execute(sql)
            dataframe = DataFrame(data=data.fetchall(), columns=data.keys())
        return dataframe

    async def read_sql_async(self, sql: str) -> DataFrame:
        async with self._async_engine.begin() as conn:
            data = await conn.execute(text(sql))
            dataframe = DataFrame(data=data.fetchall(), columns=data.keys())
        return dataframe


db = DataBase()
