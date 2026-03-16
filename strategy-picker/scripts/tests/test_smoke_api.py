"""
stock_api.py 新增接口冒烟测试
验证 5 个复合筛选方法的调用路径、参数传递、边界返回值。
"""
import sys
import os
from unittest.mock import MagicMock, patch, call

_scripts_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(_scripts_dir)
sys.path.insert(0, _scripts_dir)

# ── mock 外部依赖 ────────────────────────────────────────────────────────────
for _m in ['sqlalchemy', 'sqlalchemy.orm', 'sqlalchemy.engine',
           'sqlalchemy.sql', 'sqlalchemy.dialects', 'pandas', 'requests']:
    sys.modules[_m] = MagicMock()
sys.modules['db_engine']                = MagicMock()
sys.modules['data_fetcher']             = MagicMock()
sys.modules['realtime_data_featcher']   = MagicMock()

import stock_api
from stock_api import StockApi
api = StockApi()

PASS = 0
FAIL = 0

def ok(name):
    global PASS; PASS += 1
    print(f"  PASS  {name}")

def fail(name, reason):
    global FAIL; FAIL += 1
    print(f"  FAIL  {name}  ->  {reason}")

# ─────────────────────────────────────────────────────────────────────────────
print("\n── get_stocks_by_industry_keyword ──")

# 关键词正确传入 query_stock_basic
with patch('stock_api.query_stock_basic', return_value=[]) as m:
    api.get_stocks_by_industry_keyword('半导体')
    kw = m.call_args.kwargs if m.call_args.kwargs else {}
    if kw.get('industry_keyword') == '半导体':
        ok('industry_keyword 参数透传')
    else:
        fail('industry_keyword 参数透传', f"kwargs={kw}")

# market 参数也透传
with patch('stock_api.query_stock_basic', return_value=[]) as m:
    api.get_stocks_by_industry_keyword('芯片', market='科创板')
    kw = m.call_args.kwargs if m.call_args.kwargs else {}
    if kw.get('market') == '科创板':
        ok('market 参数透传')
    else:
        fail('market 参数透传', f"kwargs={kw}")

# ─────────────────────────────────────────────────────────────────────────────
print("\n── get_latest_income ──")

# 无数据返回 None
with patch('stock_api.query_income', return_value=[]):
    r = api.get_latest_income('600519.SH')
    if r is None:
        ok('无数据返回 None')
    else:
        fail('无数据返回 None', f"got {r!r}")

# 有数据返回第一条
mock_inc = MagicMock()
with patch('stock_api.query_income', return_value=[mock_inc]):
    r = api.get_latest_income('600519.SH')
    if r is mock_inc:
        ok('有数据返回 Income 对象')
    else:
        fail('有数据返回 Income 对象', f"got {r!r}")

# 调用参数：report_type="1", limit=1, order_by DESC
with patch('stock_api.query_income', return_value=[]) as m:
    api.get_latest_income('000001.SZ')
    kw = m.call_args.kwargs if m.call_args.kwargs else {}
    if kw.get('limit') == 1 and kw.get('report_type') == '1' and 'DESC' in kw.get('order_by',''):
        ok('limit=1 & report_type=1 & order_by DESC')
    else:
        fail('limit=1 & report_type=1 & order_by DESC', f"kwargs={kw}")

# ─────────────────────────────────────────────────────────────────────────────
print("\n── filter_stocks_by_fundamentals ──")

# daily_basic 为空 → 返回 []
with patch('stock_api.query_daily_basic', return_value=[]):
    r = api.filter_stocks_by_fundamentals('2026-03-14', pe_ttm_max=20, mv_min_yi=100)
    if r == []:
        ok('daily_basic 为空 → []')
    else:
        fail('daily_basic 为空 → []', f"got {r!r}")

# 亏损股（pe_ttm <= 0）被过滤
_loss = MagicMock(); _loss.pe_ttm = -5;  _loss.total_mv = 2_000_000; _loss.ts_code = 'A'
_good = MagicMock(); _good.pe_ttm = 15;  _good.total_mv = 2_000_000; _good.ts_code = 'B'
with patch('stock_api.query_daily_basic', return_value=[_loss, _good]), \
     patch('stock_api.query_income', return_value=[]):
    r = api.filter_stocks_by_fundamentals('2026-03-14')
    codes = [x['ts_code'] for x in r]
    if 'A' not in codes and 'B' in codes:
        ok('亏损股 pe_ttm<=0 被过滤')
    else:
        fail('亏损股 pe_ttm<=0 被过滤', f"codes={codes}")

# pe_ttm_max 过滤
_hi = MagicMock(); _hi.pe_ttm = 50; _hi.total_mv = 500_000; _hi.ts_code = 'C'
_lo = MagicMock(); _lo.pe_ttm = 10; _lo.total_mv = 500_000; _lo.ts_code = 'D'
with patch('stock_api.query_daily_basic', return_value=[_hi, _lo]), \
     patch('stock_api.query_income', return_value=[]):
    r = api.filter_stocks_by_fundamentals('2026-03-14', pe_ttm_max=20)
    codes = [x['ts_code'] for x in r]
    if 'C' not in codes and 'D' in codes:
        ok('pe_ttm_max 过滤生效')
    else:
        fail('pe_ttm_max 过滤生效', f"codes={codes}")

# mv_min_yi 过滤（100亿 = 1,000,000 万元）
_small = MagicMock(); _small.pe_ttm = 10; _small.total_mv = 500_000;   _small.ts_code = 'E'
_big   = MagicMock(); _big.pe_ttm   = 10; _big.total_mv   = 2_000_000; _big.ts_code   = 'F'
with patch('stock_api.query_daily_basic', return_value=[_small, _big]), \
     patch('stock_api.query_income', return_value=[]):
    r = api.filter_stocks_by_fundamentals('2026-03-14', mv_min_yi=100)
    codes = [x['ts_code'] for x in r]
    if 'E' not in codes and 'F' in codes:
        ok('mv_min_yi 过滤生效')
    else:
        fail('mv_min_yi 过滤生效', f"codes={codes}")

# roe_min 过滤
_base = MagicMock(); _base.pe_ttm = 10; _base.total_mv = 500_000; _base.ts_code = 'G'
_inc_hi = MagicMock(); _inc_hi.ts_code = 'G'; _inc_hi.end_date = '20231231'; _inc_hi.roe = 20.0
_inc_lo = MagicMock(); _inc_lo.ts_code = 'H'; _inc_lo.end_date = '20231231'; _inc_lo.roe = 5.0
_base2  = MagicMock(); _base2.pe_ttm = 10; _base2.total_mv = 500_000; _base2.ts_code = 'H'
with patch('stock_api.query_daily_basic', return_value=[_base, _base2]), \
     patch('stock_api.query_income', return_value=[_inc_hi, _inc_lo]):
    r = api.filter_stocks_by_fundamentals('2026-03-14', roe_min=15)
    codes = [x['ts_code'] for x in r]
    if 'G' in codes and 'H' not in codes:
        ok('roe_min 过滤生效')
    else:
        fail('roe_min 过滤生效', f"codes={codes}")

# top_n 截取
_stocks = []
for i in range(10):
    s = MagicMock(); s.pe_ttm = 10; s.total_mv = (10-i) * 100_000; s.ts_code = f'X{i}'
    _stocks.append(s)
with patch('stock_api.query_daily_basic', return_value=_stocks), \
     patch('stock_api.query_income', return_value=[]):
    r = api.filter_stocks_by_fundamentals('2026-03-14', top_n=3)
    if len(r) == 3:
        ok('top_n=3 截取生效')
    else:
        fail('top_n=3 截取生效', f"len={len(r)}")

# ─────────────────────────────────────────────────────────────────────────────
print("\n── scan_all_signals ──")

# 未知 signal_type 抛 ValueError
try:
    api.scan_all_signals('UNKNOWN_XYZ', '2026-03-14')
    fail('未知类型抛 ValueError', '未抛出异常')
except ValueError:
    ok('未知类型抛 ValueError')

# 已知类型正常调用，返回只含 signal==1 的 dict
# get_evening_star 是从 signals 导入到 stock_api 模块中的名字，patch 模块属性
with patch.object(api, 'get_all_symbols', return_value=['A', 'B', 'C']), \
     patch('stock_api.get_evening_star', side_effect=lambda c, d, u: 1 if c == 'B' else 0):
    r = api.scan_all_signals('EVENING_STAR', '2026-03-14')
    if r == {'B': 1}:
        ok('只返回 signal==1 的股票')
    else:
        fail('只返回 signal==1 的股票', f"got {r!r}")

# codes 参数限制扫描范围，不调用 get_all_symbols
_called = []
def _fake_morning_star(c, d, u):
    _called.append(c)
    return 0
with patch('stock_api.get_morning_star', side_effect=_fake_morning_star):
    r = api.scan_all_signals('MORNING_STAR', '2026-03-14', codes=['A', 'B'])
    if set(_called) == {'A', 'B'}:
        ok('codes 参数限制扫描范围')
    else:
        fail('codes 参数限制扫描范围', f"called with {_called}")

# ─────────────────────────────────────────────────────────────────────────────
print("\n── get_period_return ──")

# 数据不足（< 2根K线）→ None
with patch('stock_api.query_daily_kline', return_value=[MagicMock()]):
    r = api.get_period_return('600519.SH', '2026-01-01', '2026-03-14')
    if r is None:
        ok('不足2根K线返回 None')
    else:
        fail('不足2根K线返回 None', f"got {r!r}")

# 无复权：收益率 = (close_e - close_s) / close_s * 100
_k1 = MagicMock(); _k1.close = 100.0; _k1.date = '2026-01-02'
_k2 = MagicMock(); _k2.close = 110.0; _k2.date = '2026-03-14'
with patch('stock_api.query_daily_kline', return_value=[_k1, _k2]):
    r = api.get_period_return('600519.SH', '2026-01-02', '2026-03-14', use_adjusted=False)
    expected = round((110 - 100) / 100 * 100, 4)
    if r is not None and abs(r - expected) < 1e-6:
        ok(f'无复权收益率计算正确 ({r}%)')
    else:
        fail('无复权收益率计算正确', f"expected {expected}, got {r!r}")

# 后复权：收益率 = (close_e * adj_e - close_s * adj_s) / (close_s * adj_s) * 100
_b1 = MagicMock(); _b1.trade_date = '2026-01-02'; _b1.adj_factor = 2.0
_b2 = MagicMock(); _b2.trade_date = '2026-03-14'; _b2.adj_factor = 4.0
with patch('stock_api.query_daily_kline', return_value=[_k1, _k2]), \
     patch('stock_api.query_daily_basic', return_value=[_b1, _b2]):
    r = api.get_period_return('600519.SH', '2026-01-02', '2026-03-14', use_adjusted=True)
    expected = round((110 * 4.0 - 100 * 2.0) / (100 * 2.0) * 100, 4)
    if r is not None and abs(r - expected) < 1e-6:
        ok(f'后复权收益率计算正确 ({r}%)')
    else:
        fail('后复权收益率计算正确', f"expected {expected}, got {r!r}")

# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{'='*50}")
print(f"结果: {PASS} 通过  {FAIL} 失败")
print('='*50)
