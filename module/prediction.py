from inspect import signature
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, Optional
from pandas.core.frame import DataFrame
from pandas.core.series import Series

from core.publisher import Publisher
from core.config import settings


class Prediction(Publisher):
    def __init__(self, events=None, **kwargs: Dict[str, Any]):
        super(Prediction, self).__init__(events=events)
        self.__dict__.update(kwargs)
        self.register()
        self.notify(event='instantiate',
                    message=f'''instantiated at {datetime.now().strftime('%Y-%m-%d %H:%M')}''')
        self.pred_data = pd.DataFrame()

# functions inside the class should be decorated with something like

#   @notify.get_data
    def prediction_data(self, month: int = 6, sum: bool = False):
        self.notify(event='data_update', message=f'retriving prediction_data')
        if (not self.pred_data.empty) and (self.pred_data.shape[1] == 2+2*month):
            return self.pred_data
        i = 3 + month
        self.pred_data = pd.read_excel('0430预估.xlsm', sheet_name='分站点预估')
        self.pred_data.rename(columns=self.pred_data.iloc[0], inplace=True)
        self.pred_data = self.pred_data.iloc[1:, np.r_[0, 1, 3:i]]
        self.pred_data.columns = ['sku', 'country'] + [pd.to_datetime(
            i, format='%Y%m', errors='ignore').strftime('%Y-%m') for i in self.pred_data.columns[2:]]
        self.pred_data['sku'] = self.pred_data['sku'].apply(lambda x: str(x))
        self.pred_data['country'] = self.pred_data['country'].apply(lambda x: [settings.COUNTRY_SUB.get(
            country) for country in settings.COUNTRY_SUB.keys() if (country in x)] or x).apply(lambda x: x[0])

        self.pred_data = self.pred_data.groupby(
            ['sku', 'country']).agg(np.sum)
        self.pred_data.reset_index(inplace=True)
        for month in range(month):
            self.pred_data[f'predsum_{self.pred_data.iloc[:, 2:2+(month+1)].columns[month]}'] = self.pred_data.iloc[:,
                                                                                                                    2: 2+(month+1)].sum(axis=1)
        self.pred_data.iloc[:, 2:] = self.pred_data.iloc[:, 2:].astype(int)
        return self.pred_data
