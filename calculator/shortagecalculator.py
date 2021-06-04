import sys
import pandas as pd
import numpy as np

from battery import Battery

from config import settings
from pandas.core.frame import DataFrame
from pandas.core.series import Series
from pydantic import BaseModel
from typing import TypeVar, Set, Optional


pd.options.mode.chained_assignment = None  # default='warn'


class ShortageCalculator:
    def __init__(self):
        self.sto_data = pd.DataFrame()
        self.pred_data = pd.DataFrame()
        self.shortage = pd.DataFrame()

    def get_ori_sku(self, sku: str) -> str:
        assert sys.version_info >= (
            3, 9), 'this script should be running at python 3.9 or higher'
        sku = str(sku).strip()
        for pfix in settings.PRE_FIX:
            sku = sku.removeprefix(pfix)
        for sfix in settings.SUR_FIX:
            sku = sku.removesuffix(sfix)
        for other in settings.CNT:
            sku = sku.replace(other, '')
        return sku

    def get_sto_data(self) -> DataFrame:
        self.sto_data = Battery(data_module='storage',
                                country='us').get_data('storage_data')
        return self.sto_data

    def get_sku_set(self, sto_data: Optional[DataFrame] = None) -> Set:
        if self.sto_data.empty:
            self.sto_data = sto_data or self.get_sto_data()
        self.sku_set = {self.get_ori_sku(sku)
                        for sku in self.sto_data['sku'].unique()}
        return self.sku_set

    def get_pred_data(self, pred_data: Optional[DataFrame] = None, month: int = 6) -> DataFrame:
        if (not self.pred_data.empty) and (self.pred_data.shape[1] == 2+2*month):
            return self.pred_data
        i = 3 + month
        self.pred_data = pred_data or self.battery.read_pred_data()
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
            self.pred_data[f'pred_{self.pred_data.iloc[:, 2:2+(month+1)].columns[month]}'] = self.pred_data.iloc[:,
                                                                                                                 2:2+(month+1)].sum(axis=1)
        self.pred_data.iloc[:, 2:] = self.pred_data.iloc[:, 2:].astype(int)
        return self.pred_data

    def get_stosum(self, sto_data: Optional[DataFrame] = None) -> DataFrame:
        if (not self.sto_data.empty) and ('仓库' not in self.sto_data.columns):
            return self.sto_data
        else:
            sto_data = sto_data or self.get_sto_data()
        self.sto_data['p_sku'] = self.sto_data['p_sku'].apply(
            lambda x: self.get_ori_sku(x))
        self.sto_data.rename(columns={'仓库': 'country'}, inplace=True)
        self.sto_data['country'] = self.sto_data['country'].apply(lambda x: [settings.COUNTRY_SUB.get(
            country) for country in settings.COUNTRY_SUB.keys() if (country in x)] or x).apply(lambda x: x[0])
        self.sto_data.reset_index(inplace=True)

        temp = self.sto_data[['ssku', 'p_sku', 'country']].copy()
        self.sto_data = self.sto_data.groupby(['p_sku', 'country'])[
            'storage'].agg(np.sum).reset_index()
        self.sto_data = pd.merge(
            self.sto_data, temp, how='left', on=['p_sku', 'country'])
        self.sto_data.drop_duplicates(inplace=True)
        self.sto_data[['ssku', 'p_sku', 'country', 'storage', 'ssku']]
        return self.sto_data

    def get_shortage(
            self, sku_series: Optional[Series] = None,
            pred_data: Optional[DataFrame] = None,
            sto_data: Optional[DataFrame] = None,
            month: int = 6
    ) -> DataFrame:
        if self.shortage.empty or self.month != month:
            pred_data = pred_data or self.get_pred_data(month=month)
            sto_data = sto_data or self.get_stosum()
            pred_data = pred_data.iloc[:, np.r_[0, 1, (month+2):2*(month+1)]]
            self.shortage = pd.merge(sto_data[sto_data['ssku'].isin(
                pred_data['sku'])], pred_data, how='left', left_on=['ssku', 'country'], right_on=['sku', 'country'])
            for month in range(month):
                self.shortage[f'sho_{(pred_data.iloc[:, 2:2+(month+1)].columns[month])}'] = self.shortage['storage'] - \
                    self.shortage[f'{pred_data.iloc[:, 2:2+(month+1)].columns[month]}']
            self.shortage.columns = list(self.shortage.columns[:-month]) + list(
                self.shortage.columns[-month:].map(lambda x: x.replace('pred_', '')))
            self.shortage.drop_duplicates(inplace=True)
            self.shortage.drop(columns=['sku'], inplace=True)
            self.month = month
        if not sku_series:
            try:
                self.sku_series = pd.read_clipboard(header=None)
                self.sku_series.rename(columns={0: 'sku'}, inplace=True)
                if 'sku' in self.sku_series.iloc[0, 0].lower():
                    self.sku_series = self.sku_series.rename(
                        columns={0: 'sku'}).drop(self.sku_series.index[0])
            except:
                print('fail copying sku')
                return self.shortage
        elif type(sku_series) != list and type(sku_series) != tuple:
            temp = list()
            temp.append(str(sku_series))
            sku_series = temp.copy()
        sku_series = sku_series or self.sku_series
        self.sku_series = pd.DataFrame(sku_series, columns=['sku'])
        self.sku_series = self.sku_series.applymap(
            lambda x: self.get_ori_sku(x))
        self.desired_shortage = self.shortage[self.shortage['p_sku'].isin(
            self.sku_series['sku'])]
        cols = list(self.desired_shortage.columns)
        a, b = cols.index('country'), cols.index('ssku')
        cols[b], cols[a] = cols[a], cols[b]
        self.desired_shortage = self.desired_shortage[cols]
        if not self.desired_shortage.empty:
            self.desired_shortage.to_clipboard(excel=True, index=False)
        return self.desired_shortage


if __name__ == "__main__":
    ShortageCalculator().get_shortage()

shortagecalculator = ShortageCalculator()
