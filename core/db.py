import os
import sqlalchemy
from typing import Dict, List, Union, Optional, Any

from core.config import settings
from dotenv import load_dotenv
from sqlalchemy import create_engine
from pandas.core.frame import DataFrame
from pandas.core.series import Series


class DataBase:
    def __init__(self):
        self.__db_engine_url = ''

    def set_db(self, **kwargs: Dict[str, Any]):
        dirname = os.path.dirname(__file__)
        filename = os.path.join(dirname, '.env')
        load_dotenv(filename)
        db_params = {key: (os.getenv(key) if not kwargs.get(
            key) else kwargs.get(key)) for key in settings.DB_PARAMS.keys()}
        self.__db_engine_url = f'''{db_params['db']}+{db_params['db_driver']}://{db_params['db_user']}:{db_params['db_password']}@{db_params['db_host']}'''
        if db_params['db_schema']:
            self.__db_engine_url = self.__db_engine_url + \
                f'''/{db_params['db_schema']}'''

    @property
    def engine(self) -> Any:
        if not self.__db_engine_url:
            self.set_db(db='mysql', db_driver='pymysql')
        return create_engine(self.__db_engine_url)

    @property
    def con(self) -> Any:
        con = self.engine.connect()
        return con

    @staticmethod
    def set_column_types(df: Optional[DataFrame] = None) -> dict:
        if not df:
            print("Input is empty")

        dtypedict = {}
        for column, dtype in zip(df.columns, df.dtypes):
            if "object" in str(dtype):
                dtypedict.update(
                    {column: sqlalchemy.types.NVARCHAR(length=255)})

            if "datetime" in str(dtype):
                dtypedict.update({column: sqlalchemy.types.Date()})

            if "float" in str(dtype):
                dtypedict.update(
                    {column: sqlalchemy.types.Float(precision=3, asdecimal=True)})

            if "int" in str(dtype):
                dtypedict.update({column: sqlalchemy.types.INT()})
        return dtypedict


db = DataBase()
