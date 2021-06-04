import pandas as pd
import numpy as np
from core.battery import Battery
from calculator.shortagecalculator import shortagecalculator
from celery import Celery
import pandas as pd
import numpy as np
from calculator.shortagecalculator import shortagecalculator
from core.battery import Battery

app = Celery(
    'tasks', broker='amqps://b-ab4aee85-b458-4b7b-8f91-85efe84180ea.mq.ap-east-1.amazonaws.com:5671')


@app.task
def add(x, y):
    return x + y


class OrderingData:

    gn = pd.read_excel(
        'G:\\InternalResource_2021-05-21\\国内库存明细(进销存).xlsx', sheet_name='备货SKU对应出库SKU')
    gn = gn[['SKU', 'P_SKU', '倍数']]
    gn.columns = ['sku', 'p_sku', 'ratio']
    gn = gn[gn['p_sku'].notna()]
    pred_data = pd.read_excel('518预估.xlsx')
    pred_data.loc[pred_data['site'] == 'US', 'site'] = '官网'

    fd = pd.read_excel('录入预估-2021.05.14.xlsx')
    fd = fd.iloc[:, 1:11]
    fd.columns = ['sku', 'site', '2021-05', '2021-06', '2021-07',
                '2021-08', '2021-09', '2021-10', '2021-011', '2021-12']
    for month in range(8):
        fd[f'predsum_{fd.iloc[:, 2:2+(month+1)].columns[month]}'] = fd.iloc[:,
                                                                            2: 2+(month+1)].sum(axis=1)
    fd.iloc[:, 2:] = fd.iloc[:, 2:].fillna(0).astype('int')
    fd = fd.iloc[:, :-2]
    fd.columns = pred_data.columns
    pred_data = pred_data.append(fd)
    pred_data = pd.merge(pred_data, gn[['sku', 'ratio']], how='left', on='sku')

    temp = pred_data.groupby(['sku'])['2021-09'].agg(np.sum).reset_index()
    temp.columns = ['sku', 'sept_sum']
    sto_data = shortagecalculator.get_sto_data()
    sto_data = sto_data.iloc[:, :-1]
    dom_sum = sto_data.groupby(['ssku']).first()[['sz_storage', 'in_factory', 'qc']].sum(
        axis=1).reset_index().rename(columns={0: 'domestic_sum'})

    sto_data = pd.merge(sto_data, dom_sum, how='left', on='ssku')
    sto_data.loc[sto_data['domestic_sum'].duplicated(), 'domestic_sum'] = 0

    sto_sum = shortagecalculator.get_stosum(sto_data=sto_data)
    dom_sum = sto_data[['ssku', 'p_sku', 'domestic_sum']
                    ].groupby('ssku').first().reset_index()
    total_sum = pd.merge(sto_sum, dom_sum, how='left', on=['ssku', 'p_sku'])
    total_sum.rename(columns={'ssku': 'sku'}, inplace=True)
    pred_data['sku'] = pred_data['sku'].apply(lambda x: str(x))
    total_sum['sku'] = total_sum['sku'].apply(lambda x: str(x))
    pred_data = pred_data.drop_duplicates()
    total_sum.rename(columns={'country': 'site'}, inplace=True)
    data = pd.merge(pred_data, total_sum, how='left', on=['sku', 'site'])
    period_need = '2021-09'
    sept_sum = data.groupby(
        'sku')['predsum_' + period_need].agg(np.sum).reset_index()
    sept_sum.columns = ['sku', 'predsum']
    data = pd.merge(data, sept_sum, how='left', on='sku')
    data['pred_ratio'] = data[period_need]/data['predsum']
    temp = data.groupby(['sku'])[[period_need, 'storage_to_send']].agg(
        np.sum).reset_index()
    temp[period_need+'shortage'] = temp[period_need]-temp['storage_to_send']
    data = pd.merge(
        data, temp[['sku', period_need+'shortage']], how='left', on='sku')
    data['total_ordering'] = data['domestic_sum']-data[period_need+'shortage']
    data['site_ordering'] = data['total_ordering'] * data['pred_ratio']
