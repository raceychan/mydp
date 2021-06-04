import pandas as pd
from core.db import db
from typing import Dict, Any, Optional
from datetime import datetime
from pandas.core.frame import DataFrame
from pandas.core.series import Series

from core.publisher import Publisher
from core.config import settings


class Storage(Publisher):
    def __init__(self, events=None, **kwargs: Dict[str, Any]):
        super(Storage, self).__init__(events=events)
        self.__dict__.update(kwargs)
        self.register()
        self.notify(event='instantiate',
                    message=f'''instantiated at {datetime.now().strftime('%Y-%m-%d %H:%M')}''')
        self.sto_data = pd.DataFrame()

    def storage_data(self, **kwargs):
        now_date = datetime.today().strftime('%Y-%m-%d')
        pis_path = 'G:\\InternalResource_' + now_date + '\\1,仓库每日进销存报表（无公式版）.xlsx'
        self.notify(event='data_update',
                    message=f'retribing storage_data from {pis_path}')
        raw_sto = pd.read_excel(pis_path, sheet_name=None)
        if (type(self.sto_data) != dict) and ('仓库' in self.sto_data.columns):
            return self.sto_data

        for key in list(raw_sto.keys())[1:-1]:
            raw_sto[key].rename(columns=raw_sto[key].iloc[0], inplace=True)
            raw_sto[key] = raw_sto[key].iloc[1:, :]
            raw_sto[key].columns = raw_sto[key].columns.str.replace(
                '\\n', '', regex=True)
            raw_sto[key] = raw_sto[key][['SKUNo.', 'P_SKU', '仓库', '已备未发', '海外库存',
                                         'SZ仓库存数量(除去已经备货)', '工厂已下单的量', '暂收仓待检/不良', '周期', '是否续卖', '等级']]
            raw_sto[key].columns = ['ssku', 'p_sku', 'sto_name', 'stockup', 'oversea_storage',
                                    'sz_storage', 'in_factory', 'qc', 'period', 'continue', 'level']
            raw_sto[key] = raw_sto[key][~(raw_sto[key]['sto_name'] == '汇总')]
            raw_sto[key]['storage_to_send'] = raw_sto[key]['stockup'] + \
                raw_sto[key]['oversea_storage']
            raw_sto[key]['storage_sum'] = raw_sto[key]['stockup'] + \
                raw_sto[key]['oversea_storage'] + raw_sto[key]['sz_storage'] + \
                raw_sto[key]['in_factory']+raw_sto[key]['qc']
            self.sto_data = self.sto_data.append(raw_sto[key])
            self.sto_data[['ssku', 'p_sku']] = self.sto_data[['ssku', 'p_sku']].applymap(
                lambda x: str(x))
        return self.sto_data
