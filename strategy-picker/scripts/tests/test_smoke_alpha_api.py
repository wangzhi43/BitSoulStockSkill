"""
test_smoke_alpha_api.py — Alpha101 接口冒烟测试

验证 StockApi 新增的三个 Alpha 方法：
  load_alpha_data / compute_alpha / compute_alphas / get_alpha_latest
"""
import sys
import os
import numpy as np
import pandas as pd
from unittest.mock import MagicMock, patch

_scripts_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(_scripts_dir)
sys.path.insert(0, _scripts_dir)

# mock 数据库层（不依赖真实 DB）
for _m in ['sqlalchemy', 'sqlalchemy.orm', 'sqlalchemy.engine',
           'sqlalchemy.sql', 'sqlalchemy.dialects', 'requests']:
    sys.modules[_m] = MagicMock()
sys.modules['db_engine']              = MagicMock()
sys.modules['data_fetcher']           = MagicMock()
sys.modules['realtime_data_featcher'] = MagicMock()

import stock_api
from stock_api import StockApi

# ── 构造合成面板数据（与 test_alpha101 保持一致）────────────────────────────
np.random.seed(0)
N_DATES, N_STOCKS = 100, 10
dates  = pd.date_range('2025-01-02', periods=N_DATES, freq='B')
codes  = [f'S{i:02d}' for i in range(N_STOCKS)]

_base  = 10 + np.cumsum(np.random.randn(N_DATES, N_STOCKS) * 0.02, axis=0)
_base  = np.abs(_base) + 1
_close  = pd.DataFrame(_base, index=dates, columns=codes)
_open   = pd.DataFrame(_base * 0.99, index=dates, columns=codes)
_high   = pd.DataFrame(np.maximum(_base * 1.01, _base), index=dates, columns=codes)
_low    = pd.DataFrame(np.minimum(_base * 0.99, _base), index=dates, columns=codes)
_vol    = pd.DataFrame(np.abs(np.random.randn(N_DATES, N_STOCKS)) * 1e6 + 5e5, index=dates, columns=codes)
_amt    = _vol * _close
_vwap   = (_open + _high + _low + _close) / 4
_ret    = _close.pct_change()
_ind    = pd.DataFrame({'S00':'A','S01':'A','S02':'B','S03':'B','S04':'C',
                        'S05':'C','S06':'A','S07':'B','S08':'C','S09':'A'}, index=dates)

_FAKE_DATA = dict(open=_open, high=_high, low=_low, close=_close,
                  volume=_vol, amount=_amt, vwap=_vwap, returns=_ret, ind=_ind)

# ── 测试框架 ─────────────────────────────────────────────────────────────────
PASS = FAIL = 0
ERRORS = []

def ok(name):
    global PASS; PASS += 1
    print(f'  PASS  {name}')

def fail(name, reason):
    global FAIL; FAIL += 1
    ERRORS.append(f'{name}: {reason}')
    print(f'  FAIL  {name}  ->  {reason}')

api = StockApi()

# ── 辅助：patch load_alpha_data 返回合成数据 ─────────────────────────────────
def _with_fake_data(fn):
    with patch.object(api, 'load_alpha_data', return_value=_FAKE_DATA):
        return fn()

# ── 测试 1: load_alpha_data 调用 AlphaDataLoader.load ────────────────────────
print('\n── Alpha API 冒烟测试 ──')

try:
    with patch('stock_api.AlphaDataLoader') as MockLoader:
        MockLoader.return_value.load.return_value = _FAKE_DATA
        result = api.load_alpha_data(['S00'], '2025-01-01', '2025-12-31')
    assert result is _FAKE_DATA
    ok('load_alpha_data 调用 AlphaDataLoader.load')
except Exception as e:
    fail('load_alpha_data 调用 AlphaDataLoader.load', str(e))

# ── 测试 2: load_alpha_data 数据为空返回 {} ───────────────────────────────────
try:
    with patch('stock_api.AlphaDataLoader') as MockLoader:
        MockLoader.return_value.load.return_value = {}
        result = api.load_alpha_data([], '2025-01-01', '2025-01-02')
    assert result == {}
    ok('load_alpha_data 空数据返回 {}')
except Exception as e:
    fail('load_alpha_data 空数据返回 {}', str(e))

# ── 测试 3: compute_alpha 返回正确形状 DataFrame ──────────────────────────────
try:
    df = _with_fake_data(lambda: api.compute_alpha(codes, '2025-01-01', '2025-12-31', 1))
    assert isinstance(df, pd.DataFrame), f'返回类型: {type(df)}'
    assert df.shape == (N_DATES, N_STOCKS), f'形状: {df.shape}'
    ok('compute_alpha(1) 返回正确形状 DataFrame')
except Exception as e:
    fail('compute_alpha(1) 返回正确形状 DataFrame', str(e))

# ── 测试 4: compute_alpha 数据为空返回 None ───────────────────────────────────
try:
    with patch.object(api, 'load_alpha_data', return_value={}):
        result = api.compute_alpha([], '2025-01-01', '2025-12-31', 1)
    assert result is None
    ok('compute_alpha 数据为空返回 None')
except Exception as e:
    fail('compute_alpha 数据为空返回 None', str(e))

# ── 测试 5: compute_alpha 非法编号抛 ValueError ───────────────────────────────
try:
    try:
        _with_fake_data(lambda: api.compute_alpha(codes, '2025-01-01', '2025-12-31', 999))
        fail('compute_alpha 非法编号抛 ValueError', '未抛出异常')
    except ValueError:
        ok('compute_alpha 非法编号抛 ValueError')
except Exception as e:
    fail('compute_alpha 非法编号抛 ValueError', str(e))

# ── 测试 6: compute_alphas 指定列表 ──────────────────────────────────────────
try:
    results = _with_fake_data(
        lambda: api.compute_alphas(codes, '2025-01-01', '2025-12-31', alphas=[1, 2, 3])
    )
    assert isinstance(results, dict), f'返回类型: {type(results)}'
    assert set(results.keys()) == {'alpha001', 'alpha002', 'alpha003'}, f'keys: {results.keys()}'
    for name, df in results.items():
        assert isinstance(df, pd.DataFrame), f'{name} 不是 DataFrame'
    ok('compute_alphas([1,2,3]) 返回正确 dict')
except Exception as e:
    fail('compute_alphas([1,2,3]) 返回正确 dict', str(e))

# ── 测试 7: compute_alphas 数据为空返回 {} ───────────────────────────────────
try:
    with patch.object(api, 'load_alpha_data', return_value={}):
        result = api.compute_alphas([], '2025-01-01', '2025-12-31', alphas=[1])
    assert result == {}
    ok('compute_alphas 数据为空返回 {}')
except Exception as e:
    fail('compute_alphas 数据为空返回 {}', str(e))

# ── 测试 8: get_alpha_latest 返回 Series（降序排列）─────────────────────────
try:
    s = _with_fake_data(
        lambda: api.get_alpha_latest(codes, '2025-01-01', '2025-12-31', alpha_num=1)
    )
    assert isinstance(s, pd.Series), f'返回类型: {type(s)}'
    assert s.is_monotonic_decreasing, '未按降序排列'
    assert s.notna().all(), '存在 NaN'
    ok('get_alpha_latest 返回降序 Series（无 NaN）')
except Exception as e:
    fail('get_alpha_latest 返回降序 Series（无 NaN）', str(e))

# ── 测试 9: get_alpha_latest 数据为空返回 None ───────────────────────────────
try:
    with patch.object(api, 'load_alpha_data', return_value={}):
        result = api.get_alpha_latest([], '2025-01-01', '2025-12-31', alpha_num=1)
    assert result is None
    ok('get_alpha_latest 数据为空返回 None')
except Exception as e:
    fail('get_alpha_latest 数据为空返回 None', str(e))

# ── 汇总 ──────────────────────────────────────────────────────────────────────
print(f"\n{'='*50}")
print(f'结果: {PASS} 通过  {FAIL} 失败')
if ERRORS:
    print('\n失败详情:')
    for e in ERRORS:
        print(f'  {e}')
print('='*50)
