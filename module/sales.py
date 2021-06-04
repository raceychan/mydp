import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from pandas.core.frame import DataFrame

from core.publisher import Publisher
from core.db import db


class Sales(Publisher):

    #   @notify.init
    def __init__(self, events=None, **kwargs: Dict[str, Any]):
        super(Sales, self).__init__(events=events)
        self.__dict__.update(kwargs)
        self.register()
        self.notify(event='instantiate',
                    message=f'''instantiated at {datetime.now().strftime('%Y-%m-%d %H:%M')}''')
        self.sto_data = pd.DataFrame()

#   @notify.sql
    def sales_sql(self, country: str):
        _sales_sql = f'''
                            select '{country}' as country, sku, purchase_date as date, units_ordered as sales
                                from lepro_studio.le_amazon_product_statistics_daily_{country}_2020
                            union all
                            select '{country}' as country, sku, purchase_date, units_ordered as sales
                                from lepro_studio.le_amazon_product_statistics_daily_{country}_2021
                        '''
        return _sales_sql

#   @notify.data
    def sales_data(self, country: str = 'us', **kwargs):
        country = country or kwargs['country']
        with db.con as conn:
            raw_sales_data = pd.read_sql(
                sql=self.sales_sql(country), con=conn)
        target_date = datetime.today().date()-timedelta(days=2)
        raw_sales_data = raw_sales_data[raw_sales_data['date'] < target_date]
        raw_sales_data['date'] = pd.to_datetime(raw_sales_data['date'])
        return raw_sales_data
