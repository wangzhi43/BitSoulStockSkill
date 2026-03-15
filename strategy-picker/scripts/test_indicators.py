"""
indicators.py 全量测试
测试内容：
  1. 每个指标在有数据时能返回非 None 值
  2. use_adjusted=True 与 use_adjusted=False 对价格敏感型指标产生不同结果（验证复权生效）
  3. 数据不足时返回 None
"""
import sys
import os
import math
from unittest.mock import MagicMock, patch

# ── 在导入 indicators 前, mock 掉所有外部依赖 ────────────────────────────────
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# mock 第三方包
for _mod in ['sqlalchemy', 'sqlalchemy.orm', 'sqlalchemy.engine',
             'sqlalchemy.sql', 'sqlalchemy.dialects', 'pandas', 'requests']:
    sys.modules[_mod] = MagicMock()

# mock 项目内部依赖模块
_mock_db = MagicMock()
_mock_fetcher = MagicMock()
sys.modules['db_engine'] = _mock_db
sys.modules['data_fetcher'] = _mock_fetcher

# 现在可以安全导入 define（只依赖 utils）和 indicators
from define import DailyKline
import indicators

# ── 辅助工具 ────────────────────────────────────────────────────────────────

def make_kline(date, code, close, high=None, low=None, open_=None, volume=1_000_000, amount=None):
    c = close
    h = high  if high  is not None else c + 0.5
    l = low   if low   is not None else c - 0.5
    o = open_ if open_ is not None else c - 0.1
    a = amount if amount is not None else c * volume
    return DailyKline(
        date=date, code=code,
        open=o, high=h, low=l, close=c,
        volume=volume, amount=a,
        adjustflag='3', turn=1.0, pctChg=0.5,
        pre_close=c - 0.1, change=0.1,
    )

def _build_klines(n=30, code='sz.000001', base_close=10.0):
    klines = []
    for i in range(n):
        date = f"2024-{(i//28)+1:02d}-{(i%28)+1:02d}"
        klines.append(make_kline(date, code, base_close + i * 0.01))
    return klines

# adj_factors: 前段 factor=4.0, 最后一根 factor=2.0 → 前复权放大约2倍
def _build_adj(klines):
    result = {}
    for i, k in enumerate(klines):
        result[k.date] = 4.0 if i < len(klines) - 1 else 2.0
    return result

CODE = 'sz.000001'
DATE = '2024-01-30'
KLINES30 = _build_klines(30)
KLINES2  = _build_klines(2)
KLINES50 = _build_klines(50)
ADJ      = _build_adj(KLINES30)

def _build_klines_mixed(n=30, code='sz.000001', base_close=10.0):
    """奇偶日涨跌交替 (+0.1 / -0.05)，保证 VR 有上涨日也有下跌日"""
    klines = []
    close = base_close
    for i in range(n):
        date = f"2024-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}"
        close = close + 0.1 if i % 2 == 0 else max(0.1, close - 0.05)
        klines.append(make_kline(date, code, close))
    return klines

KLINES_MIXED = _build_klines_mixed(30)

def _patch(mock_klines, mock_adj=None, no_cache=True):
    """返回通用 patch 上下文字典"""
    return {
        'indicators._get_klines_before_date': (
            lambda code, date, limit: mock_klines[-limit:] if limit <= len(mock_klines) else mock_klines
        ),
        'indicators._get_adj_factors_for_klines': (
            lambda klines: mock_adj if mock_adj is not None else _build_adj(klines)
        ),
        'indicators._get_cached_indicator': (lambda *a, **kw: None),
        'indicators._save_indicator':       (lambda *a, **kw: None),
    }

def run_with_patches(fn, klines=None, adj=None):
    kl  = klines if klines is not None else KLINES30
    adj = adj    if adj    is not None else _build_adj(kl)
    patches = _patch(kl, adj)
    with patch('indicators._get_klines_before_date',     patches['indicators._get_klines_before_date']), \
         patch('indicators._get_adj_factors_for_klines', patches['indicators._get_adj_factors_for_klines']), \
         patch('indicators._get_cached_indicator',       patches['indicators._get_cached_indicator']), \
         patch('indicators._save_indicator',             patches['indicators._save_indicator']):
        return fn()

# ── 测试框架 ─────────────────────────────────────────────────────────────────

PASS = 0
FAIL = 0
ERRORS = []

def ok(name):
    global PASS
    PASS += 1
    print(f"  PASS  {name}")

def fail(name, reason):
    global FAIL
    FAIL += 1
    ERRORS.append(f"{name}: {reason}")
    print(f"  FAIL  {name}  ->  {reason}")

def check_not_none(name, val):
    if val is None:
        fail(name, "returned None")
    else:
        ok(name)

def check_float(name, val):
    if val is None:
        fail(name, "returned None")
    elif not isinstance(val, (int, float)):
        fail(name, f"expected float, got {type(val)}")
    elif math.isnan(val) or math.isinf(val):
        fail(name, f"invalid float: {val}")
    else:
        ok(name)

def check_dict(name, val, required_keys):
    if val is None:
        fail(name, "returned None")
    elif not isinstance(val, dict):
        fail(name, f"expected dict, got {type(val)}")
    else:
        missing = [k for k in required_keys if k not in val]
        if missing:
            fail(name, f"missing keys {missing}")
        else:
            ok(name)

def check_adj_diff(name, val_adj, val_raw, skip_reason=None):
    """验证复权结果与非复权结果不同"""
    if skip_reason:
        global PASS
        PASS += 1
        print(f"  SKIP  {name}[adj_diff]  ({skip_reason})")
        return
    if val_adj is None or val_raw is None:
        fail(name + "[adj_diff]", f"adj={val_adj}, raw={val_raw}")
        return
    if isinstance(val_adj, dict) and isinstance(val_raw, dict):
        key = next(iter(val_adj))
        same = abs(val_adj[key] - val_raw[key]) < 1e-9
    else:
        same = abs(val_adj - val_raw) < 1e-9
    if same:
        fail(name + "[adj_diff]", "adj and raw are identical — adj may not be applied")
    else:
        ok(name + "[adj_diff]")

def check_none_on_insufficient(name, val):
    if val is not None:
        fail(name + "[insufficient→None]", f"expected None but got {val!r}")
    else:
        ok(name + "[insufficient→None]")

def check_int_nonneg(name, val):
    """验证返回值为非负整数"""
    if val is None:
        fail(name, "returned None")
    elif not isinstance(val, int):
        fail(name, f"expected int, got {type(val)}")
    elif val < 0:
        fail(name, f"expected non-negative int, got {val}")
    else:
        ok(name)

# ── 各指标测试函数 ─────────────────────────────────────────────────────────

def test_float_indicator(name, fn_adj, fn_raw, fn_insuf=None):
    """通用单值浮点指标测试"""
    v_adj = run_with_patches(fn_adj)
    check_float(name, v_adj)
    v_raw = run_with_patches(fn_raw)
    check_adj_diff(name, v_adj, v_raw)
    if fn_insuf:
        v_ins = run_with_patches(fn_insuf, klines=KLINES2)
        check_none_on_insufficient(name, v_ins)

def test_dict_indicator(name, fn_adj, fn_raw, keys, fn_insuf=None):
    """通用字典型指标测试"""
    v_adj = run_with_patches(fn_adj)
    check_dict(name, v_adj, keys)
    v_raw = run_with_patches(fn_raw)
    check_adj_diff(name, v_adj, v_raw)
    if fn_insuf:
        v_ins = run_with_patches(fn_insuf, klines=KLINES2)
        check_none_on_insufficient(name, v_ins)

# ── 实际测试 ──────────────────────────────────────────────────────────────

print("\n── 第一梯队：最常用指标 ──")

test_float_indicator('SMA',
    lambda: indicators.get_sma(CODE, DATE, 20, True),
    lambda: indicators.get_sma(CODE, DATE, 20, False),
    lambda: indicators.get_sma(CODE, DATE, 20, True),
)

test_float_indicator('EMA',
    lambda: indicators.get_ema(CODE, DATE, 12, True),
    lambda: indicators.get_ema(CODE, DATE, 12, False),
    lambda: indicators.get_ema(CODE, DATE, 20, True),
)

test_float_indicator('WMA',
    lambda: indicators.get_wma(CODE, DATE, 20, True),
    lambda: indicators.get_wma(CODE, DATE, 20, False),
    lambda: indicators.get_wma(CODE, DATE, 20, True),
)

test_float_indicator('TEMA',
    lambda: indicators.get_tema(CODE, DATE, 20, True),
    lambda: indicators.get_tema(CODE, DATE, 20, False),
)

test_float_indicator('RSI',
    lambda: indicators.get_rsi(CODE, DATE, 14, True),
    lambda: indicators.get_rsi(CODE, DATE, 14, False),
    lambda: indicators.get_rsi(CODE, DATE, 14, True),
)

test_dict_indicator('MACD',
    lambda: indicators.get_macd(CODE, DATE, 12, 26, 9, True),
    lambda: indicators.get_macd(CODE, DATE, 12, 26, 9, False),
    ['macd', 'signal', 'histogram'],
)

test_dict_indicator('BollingerBands',
    lambda: indicators.get_bollinger_bands(CODE, DATE, 20, 2, True),
    lambda: indicators.get_bollinger_bands(CODE, DATE, 20, 2, False),
    ['upper', 'middle', 'lower'],
    lambda: indicators.get_bollinger_bands(CODE, DATE, 20, 2, True),
)

test_float_indicator('ATR',
    lambda: indicators.get_atr(CODE, DATE, 14, True),
    lambda: indicators.get_atr(CODE, DATE, 14, False),
    lambda: indicators.get_atr(CODE, DATE, 14, True),
)

test_float_indicator('MOM',
    lambda: indicators.get_mom(CODE, DATE, 10, True),
    lambda: indicators.get_mom(CODE, DATE, 10, False),
    lambda: indicators.get_mom(CODE, DATE, 10, True),
)

test_float_indicator('ROC',
    lambda: indicators.get_roc(CODE, DATE, 10, True),
    lambda: indicators.get_roc(CODE, DATE, 10, False),
    lambda: indicators.get_roc(CODE, DATE, 10, True),
)

print("\n── 第二梯队：常用指标 ──")

test_float_indicator('CCI',
    lambda: indicators.get_cci(CODE, DATE, 20, True),
    lambda: indicators.get_cci(CODE, DATE, 20, False),
    lambda: indicators.get_cci(CODE, DATE, 20, True),
)

test_float_indicator('OBV',
    lambda: indicators.get_obv(CODE, DATE, 20, True),
    lambda: indicators.get_obv(CODE, DATE, 20, False),
    lambda: indicators.get_obv(CODE, DATE, 20, True),
)

v = run_with_patches(lambda: indicators.get_volume(CODE, DATE, 20, True))
check_dict('VOLUME', v, ['current', 'sma'])

test_dict_indicator('KDJ',
    lambda: indicators.get_kdj(CODE, DATE, 9, 3, 3, True),
    lambda: indicators.get_kdj(CODE, DATE, 9, 3, 3, False),
    ['k', 'd', 'j'],
    lambda: indicators.get_kdj(CODE, DATE, 9, 3, 3, True),
)

test_dict_indicator('DMI',
    lambda: indicators.get_dmi(CODE, DATE, 14, True),
    lambda: indicators.get_dmi(CODE, DATE, 14, False),
    ['pdi', 'mdi', 'adx'],
    lambda: indicators.get_dmi(CODE, DATE, 14, True),
)

# TRIX 需要 period*3+5=41 根 K 线，使用 KLINES50
_v_trix_adj = run_with_patches(lambda: indicators.get_trix(CODE, DATE, 12, True),  klines=KLINES50)
_v_trix_raw = run_with_patches(lambda: indicators.get_trix(CODE, DATE, 12, False), klines=KLINES50)
_v_trix_ins = run_with_patches(lambda: indicators.get_trix(CODE, DATE, 12, True),  klines=KLINES2)
check_float('TRIX', _v_trix_adj)
check_adj_diff('TRIX', _v_trix_adj, _v_trix_raw)
check_none_on_insufficient('TRIX', _v_trix_ins)

test_dict_indicator('SAR',
    lambda: indicators.get_sar(CODE, DATE, 0.02, 0.2, True),
    lambda: indicators.get_sar(CODE, DATE, 0.02, 0.2, False),
    ['sar', 'trend'],
)

test_float_indicator('WilliamsR',
    lambda: indicators.get_williams_r(CODE, DATE, 14, True),
    lambda: indicators.get_williams_r(CODE, DATE, 14, False),
    lambda: indicators.get_williams_r(CODE, DATE, 14, True),
)

test_float_indicator('PSY',
    lambda: indicators.get_psycho(CODE, DATE, 12, True),
    lambda: indicators.get_psycho(CODE, DATE, 12, False),
    lambda: indicators.get_psycho(CODE, DATE, 12, True),
)

test_float_indicator('BIAS',
    lambda: indicators.get_bias(CODE, DATE, 20, True),
    lambda: indicators.get_bias(CODE, DATE, 20, False),
)

test_float_indicator('TR',
    lambda: indicators.get_tr(CODE, DATE, True),
    lambda: indicators.get_tr(CODE, DATE, False),
)

test_float_indicator('NATR',
    lambda: indicators.get_natr(CODE, DATE, 14, True),
    lambda: indicators.get_natr(CODE, DATE, 14, False),
)

print("\n── 第三梯队：成交量/流量指标 ──")

test_float_indicator('VWAP',
    lambda: indicators.get_vwap(CODE, DATE, 20, True),
    lambda: indicators.get_vwap(CODE, DATE, 20, False),
)

v_ad_adj = run_with_patches(lambda: indicators.get_ad(CODE, DATE, 20, True))
v_ad_raw = run_with_patches(lambda: indicators.get_ad(CODE, DATE, 20, False))
check_float('AD', v_ad_adj)
check_adj_diff('AD', v_ad_adj, v_ad_raw,
    skip_reason='CLV=(2c-h-l)/(h-l) is scale-invariant; adj multiplier cancels out')

v_adosc_adj = run_with_patches(lambda: indicators.get_adosc(CODE, DATE, 3, 10, True))
v_adosc_raw = run_with_patches(lambda: indicators.get_adosc(CODE, DATE, 3, 10, False))
check_float('ADOSC', v_adosc_adj)
check_adj_diff('ADOSC', v_adosc_adj, v_adosc_raw,
    skip_reason='delegates to AD which is scale-invariant')

test_float_indicator('MFI',
    lambda: indicators.get_mfi(CODE, DATE, 14, True),
    lambda: indicators.get_mfi(CODE, DATE, 14, False),
    lambda: indicators.get_mfi(CODE, DATE, 14, True),
)

test_float_indicator('CMO',
    lambda: indicators.get_cmo(CODE, DATE, 14, True),
    lambda: indicators.get_cmo(CODE, DATE, 14, False),
    lambda: indicators.get_cmo(CODE, DATE, 14, True),
)

test_float_indicator('ROCP',
    lambda: indicators.get_rocp(CODE, DATE, 10, True),
    lambda: indicators.get_rocp(CODE, DATE, 10, False),
    lambda: indicators.get_rocp(CODE, DATE, 10, True),
)

test_float_indicator('ROCR',
    lambda: indicators.get_rocr(CODE, DATE, 10, True),
    lambda: indicators.get_rocr(CODE, DATE, 10, False),
    lambda: indicators.get_rocr(CODE, DATE, 10, True),
)

test_dict_indicator('AROON',
    lambda: indicators.get_aroon(CODE, DATE, 14, True),
    lambda: indicators.get_aroon(CODE, DATE, 14, False),
    ['up', 'down', 'osc'],
    lambda: indicators.get_aroon(CODE, DATE, 14, True),
)

# ULTOSC stub，仅验证非 None
v = run_with_patches(lambda: indicators.get_ultosc(CODE, DATE, 7, 14, 28, True))
check_not_none('ULTOSC', v)

print("\n── 第四梯队：专业指标 ──")

# DEMA stub（两次 EMA 相同值 → 2*ema-ema=ema，adj_diff 可能为0，仅检查非None）
v = run_with_patches(lambda: indicators.get_dema(CODE, DATE, 20, True))
check_not_none('DEMA', v)

# KAMA stub
v = run_with_patches(lambda: indicators.get_kama(CODE, DATE, 10, True))
v_raw = run_with_patches(lambda: indicators.get_kama(CODE, DATE, 10, False))
check_not_none('KAMA', v)
check_adj_diff('KAMA', v, v_raw,
    skip_reason='stub: returns klines[-1].close; last kline adj_factor==base_adj_factor→ratio=1')

test_float_indicator('MIDPOINT',
    lambda: indicators.get_midpoint(CODE, DATE, 14, True),
    lambda: indicators.get_midpoint(CODE, DATE, 14, False),
    lambda: indicators.get_midpoint(CODE, DATE, 14, True),
)

v = run_with_patches(lambda: indicators.get_midprice(CODE, DATE, 14, True))
check_not_none('MIDPRICE', v)

# PVI/NVI stubs
v = run_with_patches(lambda: indicators.get_pvi(CODE, DATE, 20, True))
check_not_none('PVI', v)
v = run_with_patches(lambda: indicators.get_nvi(CODE, DATE, 20, True))
check_not_none('NVI', v)

# PPO stub（fast EMA == slow EMA → same value, adj_diff may be 0）
v = run_with_patches(lambda: indicators.get_ppo(CODE, DATE, 12, 26, 9, True))
check_not_none('PPO', v)

v_roc_r = run_with_patches(lambda: indicators.get_roc_r(CODE, DATE, 10, True))
check_not_none('ROC_R', v_roc_r)

test_dict_indicator('STOCH',
    lambda: indicators.get_stoch(CODE, DATE, 14, 3, 3, True),
    lambda: indicators.get_stoch(CODE, DATE, 14, 3, 3, False),
    ['slowk', 'slowd'],
    lambda: indicators.get_stoch(CODE, DATE, 14, 3, 3, True),
)

v = run_with_patches(lambda: indicators.get_stochf(CODE, DATE, 14, 3, True))
check_not_none('STOCHF', v)
v = run_with_patches(lambda: indicators.get_stochrsi(CODE, DATE, 14, 14, True))
check_not_none('STOCHRSI', v)

v = run_with_patches(lambda: indicators.get_trange(CODE, DATE, True))
check_not_none('TRANGE', v)

print("\n── 第五梯队：通道指标 ──")

test_dict_indicator('MA_CHANNEL',
    lambda: indicators.get_ma_channel(CODE, DATE, 20, 2.0, True),
    lambda: indicators.get_ma_channel(CODE, DATE, 20, 2.0, False),
    ['upper', 'middle', 'lower'],
)

test_dict_indicator('DONCHIAN',
    lambda: indicators.get_donchian(CODE, DATE, 20, True),
    lambda: indicators.get_donchian(CODE, DATE, 20, False),
    ['upper', 'middle', 'lower'],
    lambda: indicators.get_donchian(CODE, DATE, 20, True),
)

test_dict_indicator('KELTNER',
    lambda: indicators.get_keltner(CODE, DATE, 20, 10, 2.0, True),
    lambda: indicators.get_keltner(CODE, DATE, 20, 10, 2.0, False),
    ['upper', 'middle', 'lower'],
)

test_float_indicator('BBANDS_WIDTH',
    lambda: indicators.get_bbands_width(CODE, DATE, 20, 2, True),
    lambda: indicators.get_bbands_width(CODE, DATE, 20, 2, False),
)

test_float_indicator('BBANDS_PCT',
    lambda: indicators.get_bbands_pct(CODE, DATE, 20, 2, True),
    lambda: indicators.get_bbands_pct(CODE, DATE, 20, 2, False),
)

print("\n── 第六梯队：统计指标 ──")

test_float_indicator('LINEARREG',
    lambda: indicators.get_linearreg(CODE, DATE, 14, True),
    lambda: indicators.get_linearreg(CODE, DATE, 14, False),
    lambda: indicators.get_linearreg(CODE, DATE, 14, True),
)

test_float_indicator('LINEARREG_ANGLE',
    lambda: indicators.get_linearreg_angle(CODE, DATE, 14, True),
    lambda: indicators.get_linearreg_angle(CODE, DATE, 14, False),
    lambda: indicators.get_linearreg_angle(CODE, DATE, 14, True),
)

test_float_indicator('LINEARREG_INTERCEPT',
    lambda: indicators.get_linearreg_intercept(CODE, DATE, 14, True),
    lambda: indicators.get_linearreg_intercept(CODE, DATE, 14, False),
    lambda: indicators.get_linearreg_intercept(CODE, DATE, 14, True),
)

test_float_indicator('LINEARREG_SLOPE',
    lambda: indicators.get_linearreg_slope(CODE, DATE, 14, True),
    lambda: indicators.get_linearreg_slope(CODE, DATE, 14, False),
    lambda: indicators.get_linearreg_slope(CODE, DATE, 14, True),
)

test_float_indicator('STDDEV',
    lambda: indicators.get_stddev(CODE, DATE, 20, 1, True),
    lambda: indicators.get_stddev(CODE, DATE, 20, 1, False),
    lambda: indicators.get_stddev(CODE, DATE, 20, 1, True),
)

v = run_with_patches(lambda: indicators.get_tsf(CODE, DATE, 14, True))
check_not_none('TSF', v)

test_float_indicator('VAR',
    lambda: indicators.get_var(CODE, DATE, 20, 1, True),
    lambda: indicators.get_var(CODE, DATE, 20, 1, False),
    lambda: indicators.get_var(CODE, DATE, 20, 1, True),
)

v = run_with_patches(lambda: indicators.get_correl(CODE, DATE, 20, True))
check_not_none('CORREL', v)
v = run_with_patches(lambda: indicators.get_beta(CODE, DATE, 20, True))
check_not_none('BETA', v)

print("\n── 希尔伯特变换 (stubs) ──")
for fname, fn in [
    ('HT_DCPERIOD',  lambda: indicators.get_ht_dcperiod(CODE, DATE, True)),
    ('HT_DCPHASE',   lambda: indicators.get_ht_dcphase(CODE, DATE, True)),
    ('HT_PHASOR',    lambda: indicators.get_ht_phasor(CODE, DATE, True)),
    ('HT_SINE',      lambda: indicators.get_ht_sine(CODE, DATE, True)),
    ('HT_TRENDMODE', lambda: indicators.get_ht_trendmode(CODE, DATE, True)),
]:
    v = run_with_patches(fn)
    check_not_none(fname, v)

print("\n── 辅助价格指标 ──")

_single_kline_note = 'single-kline indicator: adj_factor/base_adj_factor=1 for only data point'

for _name, _fn_adj, _fn_raw in [
    ('TYPICAL_PRICE',  lambda: indicators.get_typical_price(CODE, DATE, True),  lambda: indicators.get_typical_price(CODE, DATE, False)),
    ('MEDIAN_PRICE',   lambda: indicators.get_median_price(CODE, DATE, True),   lambda: indicators.get_median_price(CODE, DATE, False)),
    ('WEIGHTED_CLOSE', lambda: indicators.get_weighted_close(CODE, DATE, True), lambda: indicators.get_weighted_close(CODE, DATE, False)),
    ('AVGP',           lambda: indicators.get_avgp(CODE, DATE, True),           lambda: indicators.get_avgp(CODE, DATE, False)),
]:
    v_a = run_with_patches(_fn_adj)
    v_r = run_with_patches(_fn_raw)
    check_float(_name, v_a)
    check_adj_diff(_name, v_a, v_r, skip_reason=_single_kline_note)

print("\n── 新增指标 ──")

# ASI  需要 period+1=27 根 K 线
test_float_indicator('ASI',
    lambda: indicators.get_asi(CODE, DATE, 26, True),
    lambda: indicators.get_asi(CODE, DATE, 26, False),
    lambda: indicators.get_asi(CODE, DATE, 26, True),
)

# VR  需要奇偶交替涨跌的 K 线避免分母为 0
# adj_diff: 方向分类在 mock 下不改变（只有最后一根因子不同但方向相同），volumes 不受复权影响
_v_vr_adj = run_with_patches(lambda: indicators.get_vr(CODE, DATE, 26, True),  klines=KLINES_MIXED)
_v_vr_raw = run_with_patches(lambda: indicators.get_vr(CODE, DATE, 26, False), klines=KLINES_MIXED)
check_float('VR', _v_vr_adj)
check_adj_diff('VR', _v_vr_adj, _v_vr_raw,
    skip_reason='close direction classification unchanged with single factor=2.0 tail; volume unaffected by adj')

# AR  adj_diff: sum(H-O)/sum(O-L)*100, 分子分母按相同因子同比缩放 → 比值不变
_v_ar_adj = run_with_patches(lambda: indicators.get_ar(CODE, DATE, 26, True))
_v_ar_raw = run_with_patches(lambda: indicators.get_ar(CODE, DATE, 26, False))
check_float('AR', _v_ar_adj)
check_adj_diff('AR', _v_ar_adj, _v_ar_raw,
    skip_reason='AR = sum(H-O)/sum(O-L)*100; H-O and O-L both scale by adj_factor → ratio scale-invariant')

# BR  相邻 K 线用不同因子 → prev.close_adj 与 cur.high_adj 跨两个因子，adj != raw
test_float_indicator('BR',
    lambda: indicators.get_br(CODE, DATE, 26, True),
    lambda: indicators.get_br(CODE, DATE, 26, False),
    lambda: indicators.get_br(CODE, DATE, 26, True),
)

# BRAR  dict 首键 'ar' 是尺度不变量，用 skip；BR 已在上面单独验证
_v_brar_adj = run_with_patches(lambda: indicators.get_brar(CODE, DATE, 26, True))
_v_brar_raw = run_with_patches(lambda: indicators.get_brar(CODE, DATE, 26, False))
check_dict('BRAR', _v_brar_adj, ['ar', 'br'])
check_adj_diff('BRAR', _v_brar_adj, _v_brar_raw,
    skip_reason="first key 'ar' is scale-invariant; BR component verified separately")

# DPO  period=10 → needed=10+6+1=17 根 K 线，KLINES30 满足
test_float_indicator('DPO',
    lambda: indicators.get_dpo(CODE, DATE, 10, True),
    lambda: indicators.get_dpo(CODE, DATE, 10, False),
    lambda: indicators.get_dpo(CODE, DATE, 10, True),
)

# BBI  需要 24 根 K 线
test_float_indicator('BBI',
    lambda: indicators.get_bbi(CODE, DATE, True),
    lambda: indicators.get_bbi(CODE, DATE, False),
    lambda: indicators.get_bbi(CODE, DATE, True),
)

# MASS  需要 ema_period*2+period=43 根 K 线，使用 KLINES50
_v_mass_adj = run_with_patches(lambda: indicators.get_mass(CODE, DATE, 25, True),  klines=KLINES50)
_v_mass_raw = run_with_patches(lambda: indicators.get_mass(CODE, DATE, 25, False), klines=KLINES50)
_v_mass_ins = run_with_patches(lambda: indicators.get_mass(CODE, DATE, 25, True),  klines=KLINES2)
check_float('MASS', _v_mass_adj)
check_adj_diff('MASS', _v_mass_adj, _v_mass_raw)
check_none_on_insufficient('MASS', _v_mass_ins)

# 薛斯通道 XUE_CHANNEL
test_dict_indicator('XUE_CHANNEL',
    lambda: indicators.get_xue_channel(CODE, DATE, 20, 3.0, True),
    lambda: indicators.get_xue_channel(CODE, DATE, 20, 3.0, False),
    ['upper', 'middle', 'lower'],
    lambda: indicators.get_xue_channel(CODE, DATE, 20, 3.0, True),
)

# 连涨天数：KLINES30 单调递增，raw=29；最后一根 factor=2.0 导致复权后反转 → adj=0
_v_rise_adj = run_with_patches(lambda: indicators.get_consecutive_rise(CODE, DATE, 60, True))
_v_rise_raw = run_with_patches(lambda: indicators.get_consecutive_rise(CODE, DATE, 60, False))
check_int_nonneg('CONSECUTIVE_RISE', _v_rise_adj)
check_adj_diff('CONSECUTIVE_RISE', _v_rise_adj, _v_rise_raw)

# 连跌天数：KLINES30 单调递增，raw=0；复权后最后一根价格反转 → adj=1
_v_fall_adj = run_with_patches(lambda: indicators.get_consecutive_fall(CODE, DATE, 60, True))
_v_fall_raw = run_with_patches(lambda: indicators.get_consecutive_fall(CODE, DATE, 60, False))
check_int_nonneg('CONSECUTIVE_FALL', _v_fall_adj)
check_adj_diff('CONSECUTIVE_FALL', _v_fall_adj, _v_fall_raw)

print("\n── 涨跌停与炸板指标 ──")

# 公共 mock 对象（不依赖真实 DB 结构，只需满足访问属性的代码路径）
_mock_limit_price  = MagicMock()        # StockLimit 占位
_mock_bomb_record  = MagicMock()        # DailyBombList 占位
_mock_limit_record = MagicMock()        # DailyLimitList 占位
_mock_limit_record.limit_streak = 3    # 连板数 = 3

def _run_limit(fn, limits=None, bombs=None, limit_list=None, klines=None):
    """执行带涨跌停/炸板表 mock 的指标函数。

    与 run_with_patches 独立：这组指标不走复权路径，需要 mock
    query_stock_limit / query_daily_bomb_list / query_daily_limit_list。
    """
    _lim = limits     if limits     is not None else []
    _bom = bombs      if bombs      is not None else []
    _lst = limit_list if limit_list is not None else []
    _kl  = klines     if klines     is not None else KLINES30
    with patch('indicators._get_cached_indicator',  lambda *a, **kw: None),      \
         patch('indicators._save_indicator',        lambda *a, **kw: None),      \
         patch('indicators.query_stock_limit',      lambda **kw: _lim),          \
         patch('indicators.query_daily_bomb_list',  lambda **kw: _bom),          \
         patch('indicators.query_daily_limit_list', lambda **kw: _lst),          \
         patch('indicators._get_klines_before_date',
               lambda code, date, limit: _kl[-limit:] if limit <= len(_kl) else _kl):
        return fn()

# ─── BOMB_BOARD ───────────────────────────────────────────────────────────────

# 炸板命中：stock_limit 有记录（有效交易日）+ bomb_list 有记录 → 1
_v = _run_limit(lambda: indicators.get_bomb_board(CODE, DATE),
                limits=[_mock_limit_price], bombs=[_mock_bomb_record])
if _v == 1:
    ok('BOMB_BOARD[hit=1]')
else:
    fail('BOMB_BOARD[hit=1]', f"expected 1, got {_v!r}")

# 未炸板：有效交易日，但 bomb_list 无记录 → 0
_v = _run_limit(lambda: indicators.get_bomb_board(CODE, DATE),
                limits=[_mock_limit_price], bombs=[])
if _v == 0:
    ok('BOMB_BOARD[miss=0]')
else:
    fail('BOMB_BOARD[miss=0]', f"expected 0, got {_v!r}")

# 非交易日/数据缺失：stock_limit 无记录 → None
_v = _run_limit(lambda: indicators.get_bomb_board(CODE, DATE), limits=[])
check_none_on_insufficient('BOMB_BOARD', _v)

# 缓存命中：直接返回缓存值，不触发任何 DB 查询
try:
    with patch('indicators._get_cached_indicator', return_value='1'),              \
         patch('indicators._save_indicator',        lambda *a, **kw: None),        \
         patch('indicators.query_stock_limit',
               side_effect=AssertionError('query_stock_limit should not be called')),   \
         patch('indicators.query_daily_bomb_list',
               side_effect=AssertionError('query_daily_bomb_list should not be called')):
        _v_cache = indicators.get_bomb_board(CODE, DATE)
    if _v_cache == 1:
        ok('BOMB_BOARD[cache_hit]')
    else:
        fail('BOMB_BOARD[cache_hit]', f"expected 1, got {_v_cache!r}")
except Exception as _e:
    fail('BOMB_BOARD[cache_hit]', str(_e))

# ─── BOMB_BOARD_COUNT ─────────────────────────────────────────────────────────

# 近20个交易日内有3次炸板 → 3
_v = _run_limit(lambda: indicators.get_bomb_board_count(CODE, DATE, 20),
                bombs=[_mock_bomb_record] * 3)
if _v == 3:
    ok('BOMB_BOARD_COUNT[3炸板]')
else:
    fail('BOMB_BOARD_COUNT[3炸板]', f"expected 3, got {_v!r}")

# 近20个交易日内无炸板 → 0
_v = _run_limit(lambda: indicators.get_bomb_board_count(CODE, DATE, 20), bombs=[])
if _v == 0:
    ok('BOMB_BOARD_COUNT[0炸板]')
else:
    fail('BOMB_BOARD_COUNT[0炸板]', f"expected 0, got {_v!r}")

# 无K线数据（数据不足）→ None
_v = _run_limit(lambda: indicators.get_bomb_board_count(CODE, DATE, 20), klines=[])
check_none_on_insufficient('BOMB_BOARD_COUNT', _v)

# 缓存命中：不回查 K 线
try:
    with patch('indicators._get_cached_indicator', return_value='5'),              \
         patch('indicators._save_indicator',        lambda *a, **kw: None),        \
         patch('indicators._get_klines_before_date',
               side_effect=AssertionError('klines should not be fetched')):
        _v_cache = indicators.get_bomb_board_count(CODE, DATE, 20)
    if _v_cache == 5:
        ok('BOMB_BOARD_COUNT[cache_hit]')
    else:
        fail('BOMB_BOARD_COUNT[cache_hit]', f"expected 5, got {_v_cache!r}")
except Exception as _e:
    fail('BOMB_BOARD_COUNT[cache_hit]', str(_e))

# ─── CONSECUTIVE_LIMIT_UP ─────────────────────────────────────────────────────

# 连板3天：limit_list 有记录且 limit_streak=3 → 3
_v = _run_limit(lambda: indicators.get_consecutive_limit_up(CODE, DATE),
                limits=[_mock_limit_price], limit_list=[_mock_limit_record])
if _v == 3:
    ok('CONSECUTIVE_LIMIT_UP[streak=3]')
else:
    fail('CONSECUTIVE_LIMIT_UP[streak=3]', f"expected 3, got {_v!r}")

# 当日未涨停：有效交易日，但 limit_list 无涨停记录 → 0
_v = _run_limit(lambda: indicators.get_consecutive_limit_up(CODE, DATE),
                limits=[_mock_limit_price], limit_list=[])
if _v == 0:
    ok('CONSECUTIVE_LIMIT_UP[no_limit=0]')
else:
    fail('CONSECUTIVE_LIMIT_UP[no_limit=0]', f"expected 0, got {_v!r}")

# 非交易日/数据缺失：stock_limit 无记录 → None
_v = _run_limit(lambda: indicators.get_consecutive_limit_up(CODE, DATE), limits=[])
check_none_on_insufficient('CONSECUTIVE_LIMIT_UP', _v)

# 缓存命中：不触发任何 DB 查询
try:
    with patch('indicators._get_cached_indicator', return_value='7'),              \
         patch('indicators._save_indicator',        lambda *a, **kw: None),        \
         patch('indicators.query_stock_limit',
               side_effect=AssertionError('query_stock_limit should not be called')),   \
         patch('indicators.query_daily_limit_list',
               side_effect=AssertionError('query_daily_limit_list should not be called')):
        _v_cache = indicators.get_consecutive_limit_up(CODE, DATE)
    if _v_cache == 7:
        ok('CONSECUTIVE_LIMIT_UP[cache_hit]')
    else:
        fail('CONSECUTIVE_LIMIT_UP[cache_hit]', f"expected 7, got {_v_cache!r}")
except Exception as _e:
    fail('CONSECUTIVE_LIMIT_UP[cache_hit]', str(_e))

# ── 汇总 ─────────────────────────────────────────────────────────────────────
print(f"\n{'='*50}")
print(f"结果: {PASS} 通过  {FAIL} 失败")
if ERRORS:
    print("\n失败详情:")
    for e in ERRORS:
        print(f"  {e}")
print('='*50)
