import pandas as pd

from typing import Any, Dict, List, Union, Optional
from random import randint
from datetime import datetime

from pydantic.main import ModelMetaclass
from pydantic import BaseModel, validator, root_validator
from pandas.core.frame import DataFrame
from pandas.core.series import Series

from core.config import defaults


class DataTemplate:
    ''' DataTemplate receives a series of dict objects then 
        validates them via pydantic module 
    '''

    def __init__(self, template: ModelMetaclass, data: DataFrame):
        self.template: ModelMetaclass = template
        self.data: Union[DataFrame, List[Dict]] = data

    def __call__(self) -> Optional[DataFrame]:
        if isinstance(self.data, DataFrame):
            return pd.DataFrame([self.template(**record).dict() for record in self.data.to_dict(orient='records')])
        elif isinstance(self.data, list):
            if isinstance(self.data[randint(0, len(self.data)-1)], dict):
                return pd.DataFrame([self.template(**record).dict() for record in self.data])
            else:
                raise Exception('unknown return')

    @property
    def default(self):
        return self.template().dict()


class DataMissingError(Exception):
    def __init__(self, sku: str, message: str) -> None:
        self.sku = sku
        self.message = message
        super().__init__(message)


class Order(BaseModel):
    sku: str = 'empty_sku'
    site: str = 'us'
    storage_to_send: Optional[int] = 0
    domestic_sum: Optional[int] = 0
    predsum: int = 0
    pred_ratio: Optional[int] = 0
    shortage: Optional[int] = 0
    total_ordering: Optional[int] = 0
    site_ordering: Optional[int] = 0
    created_at: datetime = datetime.today().date()
    updated_at: datetime = datetime.today().date()

    class Config:
        validate_assignment = True

    # @root_validator(pre=True)
    # def check_fields(cls, values):
    #     if shortage not in  values and predsum not in values:
    #       raise DataMissingError(sku=values['sku],message=
    #       'a product cant be missed both predsum and shortage')
    #    return values

    @validator('*', pre=True)
    def fill_na_with_default(cls, value, config, field):
        if pd.isna(value):
            return defaults.null
        return value
