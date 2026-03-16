"""
test_random_alpha_backtest.py — random_alpha_backtest 冒烟测试
"""
import sys
import os
import numpy as np
import pandas as pd
from unittest.mock import MagicMock, patch

_scripts_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(_scripts_dir)
sys.path.insert(0, _scripts_dir)

for _m in ['sqlalchemy', 'sqlalchemy.orm', 'sqlalchemy.engine',
           'sqlalchemy.sql', 'sqlalchemy.dialects', 'requests']:
    sys.modules[_m] = MagicMock()
sys.modules['db_engine']              = MagicMock()
sys.modules['data_fetcher']           = MagicMock()
sys.modules['realtime_data_featcher'] = MagicMock()

import stock_api
from stock_api import StockApi

# ── 合成面板数据 ────────────────────────────────────────────────────────────
np.random.seed(7)
N_DATES, N_STOCKS = 150, 20
dates  = pd.date_range('2024-06-01', periods=N_DATES, freq='B')
codes  = [f'S{i:02d}' for i in range(N_STOCKS)]

_base   = 10 + np.cumsum(np.random.randn(N_DATES, N_STOCKS) * 0.02, axis=0)
_base   = np.abs(_base) + 1
_close  = pd.DataFrame(_base,             index=dates, columns=codes)
_open   = pd.DataFrame(_base * 0.99,      index=dates, columns=codes)
_high   = pd.DataFrame(np.maximum(_base * 1.01, _base), index=dates, columns=codes)
_low    = pd.DataFrame(np.minimum(_base * 0.99, _base), index=dates, columns=codes)
_vol    = pd.DataFrame(np.abs(np.random.randn(N_DATES, N_STOCKS)) * 1e6 + 5e5,
                       index=dates, columns=codes)
_amt    = _vol * _close
_vwap   = (_open + _high + _low + _close) / 4
_ret    = _close.pct_change()
_ind    = pd.DataFrame(
    {c: ('A' if i < 7 else 'B' if i < 14 else 'C') for i, c in enumerate(codes)},
    index=dates,
)
FAKE_PANEL = dict(open=_open, high=_high, low=_low, close=_close,
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

def _run(fn, **kw):
    with patch.object(api, 'load_alpha_data', return_value=FAKE_PANEL):
        return fn(**kw)

START = '2024-09-01'
END   = '2025-01-31'

print('\n── random_alpha_backtest 冒烟测试 ──')

# ── T1: 正常调用，k=3，返回结构完整 ──────────────────────────────────────────
try:
    r = _run(api.random_alpha_backtest,
             codes=codes, max_factors=5, start_date=START, end_date=END,
             random_seed=42)
    assert 'random_k' in r,         f'缺 random_k'
    assert 'selected_factors' in r, f'缺 selected_factors'
    assert 'filter_log' in r,       f'缺 filter_log'
    assert 'final_pool' in r,       f'缺 final_pool'
    assert 'backtest' in r or 'error' in r, '缺 backtest/error'
    ok(f'T1 正常调用，random_k={r["random_k"]}，因子={r["selected_factors"]}')
except Exception as e:
    fail('T1 正常调用', str(e))

# ── T2: random_k 在 [0, max_factors] 范围内 ─────────────────────────────────
try:
    counts = set()
    for seed in range(30):
        r = _run(api.random_alpha_backtest, codes=codes, max_factors=5,
                 start_date=START, end_date=END, random_seed=seed)
        counts.add(r['random_k'])
    assert min(counts) >= 0 and max(counts) <= 5, f'k 超出范围: {counts}'
    ok(f'T2 random_k 始终在 [0,5]（30次采样出现的值: {sorted(counts)}）')
except Exception as e:
    fail('T2 random_k 范围', str(e))

# ── T3: 因子列表长度 == random_k，且无重复 ───────────────────────────────────
try:
    for seed in range(20):
        r = _run(api.random_alpha_backtest, codes=codes, max_factors=5,
                 start_date=START, end_date=END, random_seed=seed)
        k = r['random_k']
        factors = r['selected_factors']
        assert len(factors) == k,            f'seed={seed}: len={len(factors)} != k={k}'
        assert len(set(factors)) == len(factors), f'seed={seed}: 因子重复'
    ok('T3 因子列表长度 == k，且无重复（20次）')
except Exception as e:
    fail('T3 因子不重复', str(e))

# ── T4: k=0 时直接回测，不过滤 ───────────────────────────────────────────────
try:
    # 固定 seed 找一个 k=0 的场景，或直接 mock random
    import random
    rng = random.Random(99)
    while True:
        k = rng.randint(0, 5)
        if k == 0:
            seed = 99
            break
        seed += 1

    # Force k=0 by patching
    with patch.object(api, 'load_alpha_data', return_value=FAKE_PANEL), \
         patch('random.Random') as MockRng:
        mock_inst = MagicMock()
        mock_inst.randint.return_value = 0
        mock_inst.sample.return_value = []
        MockRng.return_value = mock_inst
        r = api.random_alpha_backtest(codes=codes, max_factors=5,
                                      start_date=START, end_date=END)
    assert r['random_k'] == 0
    assert r['selected_factors'] == []
    assert r['filter_log'] == []
    # k=0 时 final_pool == 全部 codes
    assert set(r['final_pool']) == set(codes), \
        f"k=0 时 final_pool 应为全部 codes，得 {len(r['final_pool'])}"
    ok('T4 k=0 不过滤，final_pool = 全部股票')
except Exception as e:
    fail('T4 k=0 不过滤', str(e))

# ── T5: backtest 字段完整，且数值合理 ────────────────────────────────────────
try:
    r = _run(api.random_alpha_backtest,
             codes=codes, max_factors=3, start_date=START, end_date=END,
             random_seed=1)
    if 'backtest' in r:
        bt = r['backtest']
        required = ['start_date', 'end_date', 'trading_days', 'initial_cash',
                    'final_value', 'total_return_pct', 'annualized_return_pct',
                    'max_drawdown_pct', 'sharpe_ratio', 'equity_curve']
        missing = [k for k in required if k not in bt]
        assert not missing, f'缺字段: {missing}'
        assert bt['trading_days'] > 0,             f'trading_days={bt["trading_days"]}'
        assert bt['max_drawdown_pct'] >= 0,        f'max_dd={bt["max_drawdown_pct"]}'
        assert len(bt['equity_curve']) == bt['trading_days'] + 1, \
            f'equity_curve 长度 {len(bt["equity_curve"])} != trading_days+1'
        assert bt['equity_curve'][0] == bt['initial_cash'], '权益曲线首值 != 初始资金'
        ok(f'T5 backtest 字段完整，total_return={bt["total_return_pct"]}%，'
           f'sharpe={bt["sharpe_ratio"]}，max_dd={bt["max_drawdown_pct"]}%')
    else:
        ok(f'T5 返回 error（k={r["random_k"]}，final_pool={r.get("final_pool_count")}）: {r.get("error")}')
except Exception as e:
    fail('T5 backtest 字段完整性', str(e))

# ── T6: 股票池为空返回 error ──────────────────────────────────────────────────
try:
    with patch.object(api, 'load_alpha_data', return_value=FAKE_PANEL):
        r = api.random_alpha_backtest(codes=[], max_factors=3,
                                      start_date=START, end_date=END)
    assert 'error' in r and '空' in r['error']
    ok('T6 股票池为空返回 error')
except Exception as e:
    fail('T6 股票池为空', str(e))

# ── T7: 面板数据为空返回 error ────────────────────────────────────────────────
try:
    with patch.object(api, 'load_alpha_data', return_value={}):
        r = api.random_alpha_backtest(codes=codes, max_factors=3,
                                      start_date=START, end_date=END, random_seed=1)
    assert 'error' in r
    ok('T7 面板数据为空返回 error')
except Exception as e:
    fail('T7 面板数据为空', str(e))

# ── T8: random_seed 固定时结果可复现 ────────────────────────────────────────
try:
    r1 = _run(api.random_alpha_backtest, codes=codes, max_factors=5,
              start_date=START, end_date=END, random_seed=123)
    r2 = _run(api.random_alpha_backtest, codes=codes, max_factors=5,
              start_date=START, end_date=END, random_seed=123)
    assert r1['selected_factors'] == r2['selected_factors'], \
        f'相同 seed 结果不同: {r1["selected_factors"]} vs {r2["selected_factors"]}'
    ok(f'T8 random_seed=123 可复现（因子={r1["selected_factors"]}）')
except Exception as e:
    fail('T8 random_seed 可复现', str(e))

# ── T9: 默认日期（不传 start_date / end_date）不报错 ──────────────────────────
try:
    r = _run(api.random_alpha_backtest, codes=codes, random_seed=5)
    assert 'random_k' in r
    ok('T9 默认日期不报错')
except Exception as e:
    fail('T9 默认日期', str(e))

# ── T10: filter_log 记录条数 == len(selected_factors) ───────────────────────
try:
    for seed in [0, 1, 7, 42, 99]:
        r = _run(api.random_alpha_backtest, codes=codes, max_factors=5,
                 start_date=START, end_date=END, random_seed=seed)
        k = r['random_k']
        assert len(r['filter_log']) == k, \
            f'seed={seed}: filter_log 长度 {len(r["filter_log"])} != k={k}'
    ok('T10 filter_log 长度 == random_k（5 个 seed）')
except Exception as e:
    fail('T10 filter_log 长度', str(e))

# ── 汇总 ─────────────────────────────────────────────────────────────────────
print(f"\n{'='*50}")
print(f'结果: {PASS} 通过  {FAIL} 失败')
if ERRORS:
    print('\n失败详情:')
    for e in ERRORS:
        print(f'  {e}')
print('='*50)
