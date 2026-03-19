"""
test_moe_signal.py — 模拟外部agent调用MoE分析股票买卖信号
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from stock_api import StockApi
from track_logger import TrackLogger
import tempfile

api = StockApi(TrackLogger(os.path.join(tempfile.gettempdir(), 'test_moe.log')))

code = '600519.SH'
result = api.get_trade_signal(code)

# 退市警告优先显示
if result.get('delist_warning'):
    print(result['delist_warning'])
    print()

# 输出分析结果
signal = result.get('signal', 'HOLD')
score  = result.get('final_score', 0)
conf   = result.get('confidence', '低')
reason = result.get('reason', '')

signal_map = {'BUY': '✅ 建议买入', 'SELL': '❌ 建议卖出', 'HOLD': '⏸ 建议持有观望'}
print(f'{code} 买卖信号分析')
print('='*40)
print(f'信号：{signal_map.get(signal, signal)}')
print(f'综合评分：{score:.4f}')
print(f'置信度：{conf}')
print(f'分析依据：{reason}')
print()

experts = result.get('experts', {})
if experts:
    print('专家评分明细：')
    for name, info in experts.items():
        name_map = {'technical': '技术指标', 'alpha': 'Alpha因子', 'fundamental': '基本面', 'behavior': '量价行为'}
        label = name_map.get(name, name)
        s = info.get('score')
        w = info.get('weight', 0)
        note = info.get('note', '')
        if s is None:
            print(f'  {label:<10} 数据不足  {note}')
        else:
            print(f'  {label:<10} 评分={s:.4f}  权重={w:.3f}')
