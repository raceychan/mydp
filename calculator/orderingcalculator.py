import pandas as pd
from calculator.shortagecalculator import shortagecalculator
from core.battery import Battery

gn = pd.read_excel(
    'G:\\InternalResource_2021-05-20\\国内库存明细(进销存).xlsx', sheet_name='备货SKU对应出库SKU')
gn = gn[['SKU', 'P_SKU', '倍数']]
gn.columns = ['sku', 'p_sku', 'ratio']
gn = gn[gn['p_sku'].notna()]
pred_data = pd.merge(pred_data, gn[['sku', 'ratio']], how='left', on='sku')
sales_data = Battery('storage').get_data('storage_data')
sto_sum = shortagecalculator.get_stosum()
sto_sum.rename(columns={'country': 'site'}, inplace=True)
temp = pred_data.groupby(['sku'])['2021-09'].agg(np.sum).reset_index()
temp.columns = ['sku', 'sept_sum']
pred_data['country_ratio'] = pred_data['2021-09']/pred_data['sept_sum']
pred_data.to_excel('pred_data0518.xlsx')
