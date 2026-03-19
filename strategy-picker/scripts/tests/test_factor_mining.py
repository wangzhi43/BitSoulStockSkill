"""
test_factor_mining.py — 因子挖矿接口测试

运行方式（在 d:\Stock 目录下）：
    cmd /c ".venv\Scripts\python bitsoulSkill\strategy-picker\scripts\tests\test_factor_mining.py > out.txt 2>&1"
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from stock_api import StockApi
from track_logger import TrackLogger
import tempfile

api = StockApi(TrackLogger(os.path.join(tempfile.gettempdir(), 'test_factor_mining.log')))
codes = api.get_all_symbols()
print(f'股票池: {len(codes)} 只')

result = api.random_alpha_backtest(
    codes=codes,
    max_screen_factors=2,
    max_signal_factors=2,
)

print('\n=== 返回字段 ===')
print(list(result.keys()))
