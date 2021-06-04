import os
import sys

import pandas as pd
import numpy as np
import datetime
import importlib

from typing import Optional, Dict, Any
from pandas.core.frame import DataFrame
from pandas.core.series import Series
from core.manager import manager


sys.path.insert(0, 'module')


class Battery:
    def __init__(self, data_module: str, **kwargs: Dict[str, Any]):
        self.module = importlib.import_module(data_module)
        self.model_generator = getattr(self.module, data_module.capitalize())
        self.model = self.model_generator(**kwargs)
        self.manager = manager

    def get_data(self, data: str, **kwargs: Dict[str, Any]):
        data_method = getattr(self.model, data)
        return data_method(**kwargs)
