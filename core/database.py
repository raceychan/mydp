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
            settings.ASYNC_DATABASE_URL, pool_pre_ping=True)
        self._engine = create_engine(
            settings.DATABASE_URL, pool_pre_ping=True)

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
    def con(self) -> Any:  # can be used directly with context manager as it was implemeted by sqlalchemy already
        con = self._engine.begin()
        return con

    @property
    def read_con(self) -> Any:
        read_con = self._engine.connect().execution_options(isolation_level="AUTOCOMMIT")
        return read_con

    @property
    async def async_read_con(self):
        async_read_con = self._async_engine.connect(
        ).execution_options(isolation_level="AUTOCOMMIT")
        return async_read_con

    def read_sql(self, sql: str) -> DataFrame:
        with self.read_con as conn:
            data = conn.execute(sql)
            dataframe = DataFrame(data=data.fetchall(), columns=data.keys())
        return dataframe

    async def async_read_sql(self, sql: str) -> DataFrame:
        async with self.async_read_con as conn:
            data = await conn.execute(text(sql))
            dataframe = DataFrame(data=data.fetchall(), columns=data.keys())
        return dataframe

db = DataBase()


