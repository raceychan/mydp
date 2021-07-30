import os
import sys

import pandas as pd
import numpy as np
import datetime
import importlib

from functools import wraps
from typing import Optional, Dict, Any, Callable, Union
from pandas.core.frame import DataFrame
from pandas.core.series import Series
from core.broker import broker


sys.path.insert(0, 'module')


class Battery:
    ''' Bridge Pattern and delegation pattern
    '''

    def __init__(self, data_module: str, **kwargs: Dict[str, Any]):
        self.module = importlib.import_module(data_module)
        self.model_generator = getattr(self.module, data_module.capitalize())
        self.model = self.model_generator(**kwargs)
        self.broker = broker

    def __getattr__(self, attr_name: str) -> Union[Any, Callable]:
        ''' Usage: sales = Battery('sales', country='us')
                       data = sales.sales_data
        '''
        attr = getattr(self.model, attr_name)
        if not callable(attr):
            return attr

        @wraps(attr)
        def wrapper(*args, **kwargs):
            return attr(*args, **kwargs)
        return wrapper

