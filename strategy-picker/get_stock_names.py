import sys
import io
import os
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(script_dir, 'scripts'))
import config, utils
from track_logger import TrackLogger
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from stock_api import StockApi

codes = ['000004.SZ', '000006.SZ', '000030.SZ', '000032.SZ', '000035.SZ', '000037.SZ', '000059.SZ', '000062.SZ', '000070.SZ', '000096.SZ', '000403.SZ', '000408.SZ', '000409.SZ', '000425.SZ', '000429.SZ', '000517.SZ', '000523.SZ', '000536.SZ', '000538.SZ', '000544.SZ', '000553.SZ', '000559.SZ', '000568.SZ', '000573.SZ', '000576.SZ', '000600.SZ', '000601.SZ', '000603.SZ', '000615.SZ', '000625.SZ']

logger_file = os.path.join(utils.get_skill_work_dir(), "log_get_names.txt")
file_logger = TrackLogger(logger_file)
api = StockApi(file_logger)
for code in codes:
    info = api.get_symbol_basic_infomation(code)
    print(f"{code}（{info.name}）")
