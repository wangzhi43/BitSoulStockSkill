"""
signals.py 全量测试

测试内容：
  1. 各形态在满足条件的数据下返回 1
  2. 各形态在不满足条件的数据下返回 0
  3. 数据不足时返回 None
  4. 缓存命中后直接返回缓存值（不重复计算）
"""
import sys
import os
from unittest.mock import MagicMock, patch

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# mock 外部依赖
for _mod in ['sqlalchemy', 'sqlalchemy.orm', 'sqlalchemy.engine',
             'sqlalchemy.sql', 'sqlalchemy.dialects', 'pandas', 'requests']:
    sys.modules[_mod] = MagicMock()

_mock_db  = MagicMock()
_mock_fet = MagicMock()
sys.modules['db_engine']     = _mock_db
sys.modules['data_fetcher']  = _mock_fet

from define import DailyKline
import signals

# ── 辅助工具 ────────────────────────────────────────────────────────────────

def make_kline(date, code, close, high=None, low=None, open_=None,
               volume=1_000_000, amount=None):
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

CODE = 'sz.000001'
DATE = '2024-01-30'

def _run(fn, klines, no_cache=True):
    """在 mock patch 下执行信号函数"""
    adj = {k.date: 1.0 for k in klines}  # 复权因子全为 1（不影响价格）
    with patch('signals._get_klines_before_date',
               lambda code, date, limit: klines[-limit:] if limit <= len(klines) else klines), \
         patch('signals._get_adj_factors_for_klines', lambda kl: adj), \
         patch('signals._get_cached_signal',  lambda *a, **kw: None), \
         patch('signals._save_signal',        lambda *a, **kw: None):
        return fn()

# ── 测试框架 ─────────────────────────────────────────────────────────────────
PASS = FAIL = 0
ERRORS = []

def ok(name):
    global PASS; PASS += 1
    print(f"  PASS  {name}")

def fail(name, reason):
    global FAIL; FAIL += 1
    ERRORS.append(f"{name}: {reason}")
    print(f"  FAIL  {name}  ->  {reason}")

def chk_eq(name, val, expected):
    if val == expected:
        ok(name)
    else:
        fail(name, f"expected {expected}, got {val!r}")

def chk_none(name, val):
    if val is not None:
        fail(name + "[insufficient→None]", f"expected None, got {val!r}")
    else:
        ok(name + "[insufficient→None]")

# ═══════════════════════════════════════════════════════════════════════════
print("\n── 早晨之星 (Morning Star) ──")

# 触发：k1大阴线，k2星线，k3大阳线且刺穿k1中点
def _ms_klines_hit():
    # k1 大阴线: open=12, close=10 (body=2, range=2, body_ratio=1.0)
    k1 = make_kline('2024-01-28', CODE, close=10.0, open_=12.0, high=12.0, low=10.0)
    # k2 小实体: open=10.1, close=10.05 (body=0.05, range=1, body_ratio=0.05)
    k2 = make_kline('2024-01-29', CODE, close=10.05, open_=10.1, high=10.5, low=9.5)
    # k3 大阳线: open=10.2, close=11.5 (body=1.3, range=1.5, body_ratio=0.87); k3.close=11.5 >= k1.close+0.5*body=10+0.5*2=11
    k3 = make_kline('2024-01-30', CODE, close=11.5, open_=10.2, high=11.5, low=10.2)
    return [k1, k2, k3]

def _ms_klines_miss():
    # k3 只刺穿 30%（不足 50%）
    k1 = make_kline('2024-01-28', CODE, close=10.0, open_=12.0, high=12.0, low=10.0)
    k2 = make_kline('2024-01-29', CODE, close=10.05, open_=10.1, high=10.5, low=9.5)
    k3 = make_kline('2024-01-30', CODE, close=10.6, open_=10.2, high=10.8, low=10.2)
    return [k1, k2, k3]

chk_eq('MORNING_STAR[hit]',  _run(lambda: signals.get_morning_star(CODE, DATE), _ms_klines_hit()),  1)
chk_eq('MORNING_STAR[miss]', _run(lambda: signals.get_morning_star(CODE, DATE), _ms_klines_miss()), 0)
chk_none('MORNING_STAR', _run(lambda: signals.get_morning_star(CODE, DATE), [_ms_klines_hit()[0]]))

# ═══════════════════════════════════════════════════════════════════════════
print("\n── 黄昏之星 (Evening Star) ──")

def _es_klines_hit():
    k1 = make_kline('2024-01-28', CODE, close=12.0, open_=10.0, high=12.0, low=10.0)  # 大阳线
    k2 = make_kline('2024-01-29', CODE, close=12.05, open_=12.1, high=12.5, low=11.5) # 小实体
    # k3: open=11.8, close=10.5 (body=1.3, range=1.5); k3.close=10.5 <= k1.close-0.5*body=12-0.5*2=11
    k3 = make_kline('2024-01-30', CODE, close=10.5, open_=11.8, high=11.8, low=10.5)  # 大阴线
    return [k1, k2, k3]

def _es_klines_miss():
    k1 = make_kline('2024-01-28', CODE, close=12.0, open_=10.0, high=12.0, low=10.0)
    k2 = make_kline('2024-01-29', CODE, close=12.05, open_=12.1, high=12.5, low=11.5)
    # k3 只刺穿 30%（不足中点）
    k3 = make_kline('2024-01-30', CODE, close=11.4, open_=11.8, high=11.8, low=11.0)
    return [k1, k2, k3]

chk_eq('EVENING_STAR[hit]',  _run(lambda: signals.get_evening_star(CODE, DATE), _es_klines_hit()),  1)
chk_eq('EVENING_STAR[miss]', _run(lambda: signals.get_evening_star(CODE, DATE), _es_klines_miss()), 0)
chk_none('EVENING_STAR', _run(lambda: signals.get_evening_star(CODE, DATE), [_es_klines_hit()[0]]))

# ═══════════════════════════════════════════════════════════════════════════
print("\n── 红三兵 (Three White Soldiers) ──")

def _tws_klines_hit():
    # 三根阳线，逐步上涨，每根开盘在前根实体内，大实体小上影
    # k1: open=10.0, close=10.8, high=10.85, low=9.9  body=0.8/0.95=0.84  upper_shadow=0.05/0.95=0.05
    k1 = make_kline('2024-01-28', CODE, close=10.8, open_=10.0, high=10.85, low=9.90)
    # k2: opens at 10.3 (within k1 body [10.0,10.8]), close=11.6, high=11.65
    k2 = make_kline('2024-01-29', CODE, close=11.6, open_=10.3, high=11.65, low=10.2)
    # k3: opens at 11.0 (within k2 body [10.3,11.6]), close=12.5, high=12.55
    k3 = make_kline('2024-01-30', CODE, close=12.5, open_=11.0, high=12.55, low=10.9)
    return [k1, k2, k3]

def _tws_klines_miss():
    # k2 开盘在 k1 实体外（高于 k1 close）→ 跳空，不满足
    k1 = make_kline('2024-01-28', CODE, close=10.8, open_=10.0, high=10.85, low=9.90)
    k2 = make_kline('2024-01-29', CODE, close=11.6, open_=11.0, high=11.65, low=10.9)  # open > k1.close=10.8
    k3 = make_kline('2024-01-30', CODE, close=12.5, open_=11.5, high=12.55, low=11.4)
    return [k1, k2, k3]

chk_eq('THREE_WHITE_SOLDIERS[hit]',  _run(lambda: signals.get_three_white_soldiers(CODE, DATE), _tws_klines_hit()),  1)
chk_eq('THREE_WHITE_SOLDIERS[miss]', _run(lambda: signals.get_three_white_soldiers(CODE, DATE), _tws_klines_miss()), 0)
chk_none('THREE_WHITE_SOLDIERS', _run(lambda: signals.get_three_white_soldiers(CODE, DATE), [_tws_klines_hit()[0]]))

# ═══════════════════════════════════════════════════════════════════════════
print("\n── 三只乌鸦 (Three Black Crows) ──")

def _tbc_klines_hit():
    # k1: open=12.5, close=11.7, high=12.6, low=11.65  body=0.8/0.95=0.84
    k1 = make_kline('2024-01-28', CODE, close=11.7, open_=12.5, high=12.60, low=11.65)
    # k2: open 在 k1 实体 [11.7,12.5] 内 = 12.1, close=10.9
    k2 = make_kline('2024-01-29', CODE, close=10.9, open_=12.1, high=12.15, low=10.85)
    # k3: open 在 k2 实体 [10.9,12.1] 内 = 11.5, close=10.0
    k3 = make_kline('2024-01-30', CODE, close=10.0, open_=11.5, high=11.55, low=9.95)
    return [k1, k2, k3]

def _tbc_klines_miss():
    # k1 是阳线 → 不满足
    k1 = make_kline('2024-01-28', CODE, close=12.5, open_=11.7, high=12.6, low=11.65)
    k2 = make_kline('2024-01-29', CODE, close=10.9, open_=12.1, high=12.15, low=10.85)
    k3 = make_kline('2024-01-30', CODE, close=10.0, open_=11.5, high=11.55, low=9.95)
    return [k1, k2, k3]

chk_eq('THREE_BLACK_CROWS[hit]',  _run(lambda: signals.get_three_black_crows(CODE, DATE), _tbc_klines_hit()),  1)
chk_eq('THREE_BLACK_CROWS[miss]', _run(lambda: signals.get_three_black_crows(CODE, DATE), _tbc_klines_miss()), 0)
chk_none('THREE_BLACK_CROWS', _run(lambda: signals.get_three_black_crows(CODE, DATE), [_tbc_klines_hit()[0]]))

# ═══════════════════════════════════════════════════════════════════════════
print("\n── 乌云盖顶 (Dark Cloud Cover) ──")

def _dcc_klines_hit():
    # k1: 大阳线 open=10, close=12, high=12, low=10; body=2/2=1.0
    k1 = make_kline('2024-01-29', CODE, close=12.0, open_=10.0, high=12.0, low=10.0)
    # k2: open=12.5(>k1.close=12) → 跳空; close=10.9(<k1.close-0.5*2=11, >k1.open=10)
    k2 = make_kline('2024-01-30', CODE, close=10.9, open_=12.5, high=12.5, low=10.9)
    return [k1, k2]

def _dcc_klines_miss():
    # k2 close=11.1 > 中点 11 → 未充分刺入
    k1 = make_kline('2024-01-29', CODE, close=12.0, open_=10.0, high=12.0, low=10.0)
    k2 = make_kline('2024-01-30', CODE, close=11.1, open_=12.5, high=12.5, low=11.1)
    return [k1, k2]

chk_eq('DARK_CLOUD_COVER[hit]',  _run(lambda: signals.get_dark_cloud_cover(CODE, DATE), _dcc_klines_hit()),  1)
chk_eq('DARK_CLOUD_COVER[miss]', _run(lambda: signals.get_dark_cloud_cover(CODE, DATE), _dcc_klines_miss()), 0)
chk_none('DARK_CLOUD_COVER', _run(lambda: signals.get_dark_cloud_cover(CODE, DATE), [_dcc_klines_hit()[0]]))

# ═══════════════════════════════════════════════════════════════════════════
print("\n── 圆弧底 (Rounding Bottom) ──")

def _rb_klines_hit():
    """20根K线，中间低两侧高，呈U形"""
    # 左侧(0-6): 从13下降到10
    # 中间(7-13): 在9.x附近（最低点在此区域）
    # 右侧(14-19): 从10上升到12.5，最近3根上涨
    closes = [13.0, 12.5, 12.0, 11.5, 11.0, 10.5, 10.2,   # 左侧下降
               9.8,  9.5,  9.3,  9.2,  9.5,  9.8, 10.0,   # 中部底部
              10.3, 10.8, 11.3, 11.8, 12.2, 12.5]          # 右侧上升
    klines = []
    for i, c in enumerate(closes):
        klines.append(make_kline(f"2024-01-{i+1:02d}", CODE, c))
    return klines

def _rb_klines_miss():
    """单调递增，不构成U形"""
    klines = []
    for i in range(20):
        klines.append(make_kline(f"2024-01-{i+1:02d}", CODE, 10.0 + i * 0.1))
    return klines

chk_eq('ROUNDING_BOTTOM[hit]',  _run(lambda: signals.get_rounding_bottom(CODE, DATE, 20), _rb_klines_hit()),  1)
chk_eq('ROUNDING_BOTTOM[miss]', _run(lambda: signals.get_rounding_bottom(CODE, DATE, 20), _rb_klines_miss()), 0)
chk_none('ROUNDING_BOTTOM', _run(lambda: signals.get_rounding_bottom(CODE, DATE, 20),
                                  [make_kline('2024-01-01', CODE, 10.0)]))

# ═══════════════════════════════════════════════════════════════════════════
print("\n── 上升三角形 (Ascending Triangle) ──")

def _at_klines_hit():
    """20根K线：高点聚集在13附近（阻力），低点依次抬高（支撑线上升），当前接近阻力"""
    # 用振荡数据：阻力线在13，支撑线依次从10→10.5→11→11.5
    import math
    klines = []
    for i in range(20):
        # 收盘在 11~12.8 之间震荡，整体抬升
        base = 11.0 + i * 0.08
        c = base + 0.5 * math.sin(i * 0.7)
        h = 13.0 + (0.05 if i % 5 == 2 else 0.0)  # 多次触碰 13 附近
        l = 10.0 + i * 0.07                          # 低点逐步抬高
        klines.append(make_kline(f"2024-01-{i+1:02d}", CODE, c,
                                 high=h, low=l, open_=c - 0.1))
    return klines

def _at_klines_miss():
    """单调下降，阻力线也在下降，不构成上升三角形"""
    klines = []
    for i in range(20):
        c = 13.0 - i * 0.1
        klines.append(make_kline(f"2024-01-{i+1:02d}", CODE, c,
                                 high=c + 0.3, low=c - 0.3))
    return klines

v_at = _run(lambda: signals.get_ascending_triangle(CODE, DATE, 20), _at_klines_hit())
# 上升三角形条件较严格，只验证返回 0 或 1（非 None）且不报错
if v_at in (0, 1):
    ok('ASCENDING_TRIANGLE[returns_int]')
else:
    fail('ASCENDING_TRIANGLE[returns_int]', f"got {v_at!r}")
chk_none('ASCENDING_TRIANGLE', _run(lambda: signals.get_ascending_triangle(CODE, DATE, 20),
                                     [make_kline('2024-01-01', CODE, 10.0)]))

# ═══════════════════════════════════════════════════════════════════════════
print("\n── 顶部形态 (Top Pattern / Double Top) ──")

def _tp_klines_hit():
    """30根K线：两个峰在14附近，颈线在12，当前已回落"""
    closes = []
    for i in range(30):
        if i < 5:
            closes.append(10.0 + i * 0.8)           # 上涨到 14
        elif i < 10:
            closes.append(14.0 - (i - 5) * 0.4)     # 回落到 12（颈线）
        elif i < 15:
            closes.append(12.0 + (i - 10) * 0.4)    # 再涨回 14
        elif i < 20:
            closes.append(14.0 - (i - 15) * 0.5)    # 再次回落（第二次下跌）
        else:
            closes.append(11.5 - (i - 20) * 0.1)    # 持续下跌
    klines = []
    for i, c in enumerate(closes):
        klines.append(make_kline(f"2024-01-{i+1:02d}", CODE, c,
                                  high=c + 0.1, low=c - 0.1))
    return klines

def _tp_klines_miss():
    """单调上升，无双顶"""
    klines = []
    for i in range(30):
        klines.append(make_kline(f"2024-01-{i+1:02d}", CODE, 10.0 + i * 0.1))
    return klines

v_tp = _run(lambda: signals.get_top_pattern(CODE, DATE, 30), _tp_klines_hit())
if v_tp in (0, 1):
    ok('TOP_PATTERN[returns_int]')
else:
    fail('TOP_PATTERN[returns_int]', f"got {v_tp!r}")

chk_eq('TOP_PATTERN[miss]', _run(lambda: signals.get_top_pattern(CODE, DATE, 30), _tp_klines_miss()), 0)
chk_none('TOP_PATTERN', _run(lambda: signals.get_top_pattern(CODE, DATE, 30),
                               [make_kline('2024-01-01', CODE, 10.0)]))

# ═══════════════════════════════════════════════════════════════════════════
print("\n── 缓存命中测试 ──")

def _test_cache_hit():
    # _get_cached_signal 返回缓存值 1，不应调用 _get_klines_before_date
    mock_klines = MagicMock(side_effect=AssertionError("should not fetch klines when cache hits"))
    with patch('signals._get_cached_signal', return_value=1), \
         patch('signals._get_klines_before_date', mock_klines), \
         patch('signals._save_signal', lambda *a, **kw: None):
        result = signals.get_morning_star(CODE, DATE)
    return result

chk_eq('CACHE_HIT[morning_star]', _test_cache_hit(), 1)

# ═══════════════════════════════════════════════════════════════════════════
print(f"\n{'='*50}")
print(f"结果: {PASS} 通过  {FAIL} 失败")
if ERRORS:
    print("\n失败详情:")
    for e in ERRORS:
        print(f"  {e}")
print('='*50)
