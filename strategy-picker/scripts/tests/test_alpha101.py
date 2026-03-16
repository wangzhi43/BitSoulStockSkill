"""
test_alpha101.py — Alpha101 全量冒烟测试

验证所有 101 个 alpha 方法：
  1. 能正常调用，不抛异常
  2. 返回值是 DataFrame，形状与输入面板一致
  3. 最新一行至少有 80% 的股票有非 NaN 值（数据充足性）
  4. 跨股票横截面不全相同（因子有区分度）
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from formulaicAlphas.alpha101 import Alpha101

# ── 构造合成面板数据 ──────────────────────────────────────────────────────────
np.random.seed(42)
N_DATES, N_STOCKS = 300, 30
dates  = pd.date_range('2024-01-02', periods=N_DATES, freq='B')
codes  = [f'S{i:03d}' for i in range(N_STOCKS)]

# 随机游走价格
base   = 10 + np.cumsum(np.random.randn(N_DATES, N_STOCKS) * 0.02, axis=0)
base   = np.abs(base) + 1  # 保证正数
close  = pd.DataFrame(base,               index=dates, columns=codes)
open_  = pd.DataFrame(base * np.random.uniform(0.98, 1.00, base.shape), index=dates, columns=codes)
high   = pd.DataFrame(base * np.random.uniform(1.00, 1.02, base.shape), index=dates, columns=codes)
low    = pd.DataFrame(base * np.random.uniform(0.97, 1.00, base.shape), index=dates, columns=codes)
# 保证 high >= close >= low
high   = pd.DataFrame(np.maximum(high.values, close.values), index=dates, columns=codes)
low    = pd.DataFrame(np.minimum(low.values,  close.values), index=dates, columns=codes)

volume = pd.DataFrame(np.abs(np.random.randn(N_DATES, N_STOCKS)) * 1e6 + 5e5, index=dates, columns=codes)
amount = volume * close  # 模拟成交额
vwap   = (open_ + high + low + close) / 4
ret    = close.pct_change()
ind    = pd.DataFrame(
    {c: ('A' if i < 10 else 'B' if i < 20 else 'C') for i, c in enumerate(codes)},
    index=dates,
)

data = dict(
    open=open_, high=high, low=low, close=close,
    volume=volume, amount=amount, vwap=vwap, returns=ret, ind=ind,
)

a = Alpha101(data)

# ── 测试框架 ──────────────────────────────────────────────────────────────────
PASS = FAIL = 0
ERRORS = []

def ok(name):
    global PASS; PASS += 1
    print(f'  PASS  {name}')

def fail(name, reason):
    global FAIL; FAIL += 1
    ERRORS.append(f'{name}: {reason}')
    print(f'  FAIL  {name}  ->  {reason}')

# 这些 alpha 产出已知二值（+1/-1）信号，其阈值按真实行情校准，
# 合成小波动数据中可能全栈落在同侧，跳过横截面区分度检验
_BINARY_ALPHAS = {51}

# ── 逐一测试 101 个 alpha ─────────────────────────────────────────────────────
print('\n── Alpha101 全量冒烟测试 ──')

for n in range(1, 102):
    name   = f'alpha{n:03d}'
    method = getattr(a, name, None)

    if method is None:
        fail(name, '方法不存在')
        continue

    try:
        result = method()
    except Exception as e:
        fail(name, f'计算抛异常: {e}')
        continue

    # 1) 类型检查
    if not isinstance(result, pd.DataFrame):
        fail(name, f'返回类型不是 DataFrame: {type(result)}')
        continue

    # 2) 形状检查
    if result.shape != (N_DATES, N_STOCKS):
        fail(name, f'形状错误: {result.shape} != ({N_DATES}, {N_STOCKS})')
        continue

    # 3) 最新行非 NaN 比例 >= 80%
    last_row   = result.iloc[-1]
    valid_rate = last_row.notna().mean()
    if valid_rate < 0.8:
        fail(name, f'最新行非 NaN 比例过低: {valid_rate:.0%}')
        continue

    # 4) 横截面不全相同（有区分度）
    #    已知二值信号 alpha 跳过此检验
    if n not in _BINARY_ALPHAS:
        valid_vals = last_row.dropna()
        if valid_vals.nunique() <= 1:
            fail(name, '最新行横截面值全相同，因子无区分度')
            continue

    ok(name)

# ── 汇总 ──────────────────────────────────────────────────────────────────────
print(f"\n{'='*50}")
print(f'结果: {PASS} 通过  {FAIL} 失败')
if ERRORS:
    print('\n失败详情:')
    for e in ERRORS:
        print(f'  {e}')
print('='*50)
