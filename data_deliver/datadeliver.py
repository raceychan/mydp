import pandas as pd
import os
import zipfile
import shutil
from pathlib import Path
from os.path import join, getsize
from datetime import datetime


class DataDeliver:
    path = 'Z:\内部参考资料\预警表（每日文件）'
    paths = sorted(Path(path).iterdir(), key=os.path.getmtime)
    current_date_path = paths[-1]
    file_date = datetime.strptime(str(current_date_path).split('\\')[-1].
                                  replace('.zip', ''), '%Y%m%d').strftime('%Y-%m-%d')
    print(current_date_path)
    unzip_dir_path = 'G:\\InternalResource_' + file_date
    pis_path = unzip_dir_path + '\\1,仓库每日进销存报表（无公式版）.xlsx'

    def __init__(self):
        pass

    def unzip_data(self, current_date_path=None, unzip_dir_path=None):
        path = 'Z:\内部参考资料\预警表（每日文件）'
        paths = sorted(Path(path).iterdir(), key=os.path.getmtime)
        current_date_path = paths[-1]
        file_date = datetime.strptime(str(current_date_path).split('\\')[-1].
                                      replace('.zip', ''), '%Y%m%d').strftime('%Y-%m-%d')
        unzip_dir_path = 'G:\\InternalResource_' + file_date

        with zipfile.ZipFile(current_date_path, 'r') as zf:
            os.mkdir(unzip_dir_path)
            for old_name in zf.namelist():
                file_size = zf.getinfo(old_name).file_size
                new_name = old_name.encode('cp437').decode('gbk')
                new_path = os.path.join(unzip_dir_path, new_name)
                if file_size > 0:
                    with open(file=new_path, mode='wb') as f:
                        f.write(zf.read(old_name))
                else:
                    os.mkdir(new_path)


dd = DataDeliver()

if __name__ == "__main__":
    dd.unzip_data()
