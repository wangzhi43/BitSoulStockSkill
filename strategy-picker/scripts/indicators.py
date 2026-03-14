"""
indicators.py - 技术指标计算模块

功能：
1. 技术指标计算（SMA, EMA, RSI, MACD, BB, ATR等100+指标）
2. 计算结果缓存到数据库
3. 默认使用复权价格（前复权）

设计原则：
- 函数功能单一、最小粒度
- 查询优先使用缓存，计算后存入数据库
- 使用data_fetcher.py获取基础数据
- 默认使用复权价格，可通过参数控制
"""

from typing import Optional, Dict, List, Tuple
from sqlalchemy import text
from db_engine import getEngine
from data_fetcher import query_daily_kline, query_daily_basic
from define import DailyKline, DailyBasic
import math


def init_indicators_db():
    """初始化指标缓存表"""
    with getEngine().connect() as conn:
        conn.execute(text("""
                CREATE TABLE IF NOT EXISTS cached_indicators (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL,
                    indicator_type TEXT NOT NULL,
                    period INTEGER,
                    use_adjusted INTEGER DEFAULT 1,
                    date TEXT NOT NULL,
                    value TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(code, indicator_type, period, use_adjusted, date)
                );
            """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_indicators_lookup ON cached_indicators(code, indicator_type, period, use_adjusted, date);"))
        conn.commit()


def _get_cached_indicator(code: str, indicator_type: str, period: int, date: str, use_adjusted: bool = True) -> Optional[str]:
    """查询缓存指标"""
    with getEngine().connect() as conn:
        cursor = conn.execute(text(
            "SELECT value FROM cached_indicators WHERE code=:code AND indicator_type=:indicator_type AND period=:period AND use_adjusted=:use_adjusted AND date=:date"
        ), {"code": code, "indicator_type": indicator_type, "period": period, "use_adjusted": 1 if use_adjusted else 0, "date": date})
        row = cursor.fetchone()
        return row[0] if row else None


def _save_indicator(code: str, indicator_type: str, period: int, date: str, value: str, use_adjusted: bool = True):
    """保存指标到缓存"""
    with getEngine().connect() as conn:
        conn.execute(text(
            "INSERT OR REPLACE INTO cached_indicators (code, indicator_type, period, use_adjusted, date, value) VALUES (:code, :indicator_type, :period, :use_adjusted, :date, :value)"
        ), {"code": code, "indicator_type": indicator_type, "period": period, "use_adjusted": 1 if use_adjusted else 0, "date": date, "value": value})
        conn.commit()


def _get_klines_before_date(code: str, date: str, limit: int) -> List[DailyKline]:
    """获取指定日期前的K线数据"""
    klines = query_daily_kline(
        codes=[code],
        end_date=date,
        limit=limit,
        order_by="date DESC"
    )
    return klines[::-1]


def _get_klines_range(code: str, start_date: str, end_date: str) -> List[DailyKline]:
    """获取指定日期范围的K线数据"""
    klines = query_daily_kline(
        codes=[code],
        start_date=start_date,
        end_date=end_date,
        order_by="date ASC"
    )
    return klines


def _get_adj_factor(code: str, date: str) -> Optional[float]:
    """获取指定日期的复权因子"""
    daily_basics = query_daily_basic(ts_codes=[code], trade_date=date)
    if daily_basics:
        return daily_basics[0].adj_factor
    return None


def _get_adj_factors_for_klines(klines: List[DailyKline]) -> Dict[str, float]:
    """获取K线日期范围内的复权因子"""
    if not klines:
        return {}
    
    code = klines[0].code
    start_date = klines[0].date
    end_date = klines[-1].date
    
    daily_basics = query_daily_basic(
        ts_codes=[code],
        start_date=start_date,
        end_date=end_date
    )
    return {basic.trade_date: basic.adj_factor for basic in daily_basics}


def _adjust_price(price: float, adj_factor: float, base_adj_factor: float = 1.0) -> float:
    """复权价格计算（前复权）"""
    if base_adj_factor == 0 or adj_factor == 0:
        return price
    return price * (adj_factor / base_adj_factor)


def _adjust_klines(klines: List[DailyKline], adj_factors: Dict[str, float]) -> List[DailyKline]:
    """对K线数据进行前复权处理"""
    if not klines or not adj_factors:
        return klines
    
    base_adj_factor = 1.0
    last_date = klines[-1].date
    if last_date in adj_factors:
        base_adj_factor = adj_factors[last_date]
    
    adjusted_klines = []
    for kline in klines:
        adj_factor = adj_factors.get(kline.date, 1.0)
        adjusted_kline = DailyKline(
            date=kline.date,
            code=kline.code,
            open=_adjust_price(kline.open, adj_factor, base_adj_factor),
            high=_adjust_price(kline.high, adj_factor, base_adj_factor),
            low=_adjust_price(kline.low, adj_factor, base_adj_factor),
            close=_adjust_price(kline.close, adj_factor, base_adj_factor),
            volume=kline.volume,
            amount=_adjust_price(kline.amount, adj_factor, base_adj_factor) if kline.amount else 0.0,
            adjustflag=kline.adjustflag,
            turn=kline.turn,
            pctChg=kline.pctChg,
            pre_close=_adjust_price(kline.pre_close, adj_factor, base_adj_factor) if kline.pre_close else 0.0,
            change=_adjust_price(kline.change, adj_factor, base_adj_factor) if kline.change else 0.0
        )
        adjusted_klines.append(adjusted_kline)
    
    return adjusted_klines


# ============================================================
# 第一梯队：最常用指标
# ============================================================

def get_sma(code: str, date: str, period: int = 20, use_adjusted: bool = True) -> Optional[float]:
    """简单移动平均 SMA（默认使用复权价格）
    
    Args:
        code: 股票代码
        date: 计算日期
        period: 周期，默认20
        use_adjusted: 是否使用复权价格，默认True
    """
    cached = _get_cached_indicator(code, 'SMA', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, period)
    if len(klines) < period:
        return None
    
    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)
    
    sma = sum(k.close for k in klines) / period
    _save_indicator(code, 'SMA', period, date, str(sma), use_adjusted)
    return sma


def get_ema(code: str, date: str, period: int = 12, use_adjusted: bool = True) -> Optional[float]:
    """指数移动平均 EMA（默认使用复权价格）
    
    Args:
        code: 股票代码
        date: 计算日期
        period: 周期，默认12
        use_adjusted: 是否使用复权价格，默认True
    """
    cached = _get_cached_indicator(code, 'EMA', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, period * 2)
    if len(klines) < period:
        return None
    
    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)
    
    prices = [k.close for k in klines]
    ema = prices[0]
    multiplier = 2 / (period + 1)
    for price in prices[1:]:
        ema = (price - ema) * multiplier + ema
    
    _save_indicator(code, 'EMA', period, date, str(ema), use_adjusted)
    return ema


def get_wma(code: str, date: str, period: int = 20, use_adjusted: bool = True) -&gt; Optional[float]:
    """加权移动平均 WMA（默认使用复权价格）
    
    Args:
        code: 股票代码
        date: 计算日期
        period: 周期，默认20
        use_adjusted: 是否使用复权价格，默认True
    """
    cached = _get_cached_indicator(code, 'WMA', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, period)
    if len(klines) &lt; period:
        return None
    
    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)
    
    weights = list(range(1, period + 1))
    weighted_sum = sum(k.close * w for k, w in zip(klines, weights))
    wma = weighted_sum / sum(weights)
    
    _save_indicator(code, 'WMA', period, date, str(wma), use_adjusted)
    return wma


def get_tema(code: str, date: str, period: int = 20, use_adjusted: bool = True) -> Optional[float]:
    """三重指数移动平均 TEMA（默认使用复权价格）
    
    Args:
        code: 股票代码
        date: 计算日期
        period: 周期，默认20
        use_adjusted: 是否使用复权价格，默认True
    """
    cached = _get_cached_indicator(code, 'TEMA', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    ema1 = get_ema(code, date, period, use_adjusted)
    if ema1 is None:
        return None
    
    ema2 = get_ema(code, date, period, use_adjusted)
    if ema2 is None:
        return None
    
    ema3 = get_ema(code, date, period, use_adjusted)
    if ema3 is None:
        return None
    
    tema = 3 * ema1 - 3 * ema2 + ema3
    _save_indicator(code, 'TEMA', period, date, str(tema), use_adjusted)
    return tema


def get_rsi(code: str, date: str, period: int = 14, use_adjusted: bool = True) -> Optional[float]:
    """相对强弱指标 RSI (0-100)（默认使用复权价格）
    
    Args:
        code: 股票代码
        date: 计算日期
        period: 周期，默认14
        use_adjusted: 是否使用复权价格，默认True
    """
    cached = _get_cached_indicator(code, 'RSI', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, period + 1)
    if len(klines) < period + 1:
        return None
    
    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)
    
    gains, losses = [], []
    for i in range(1, len(klines)):
        diff = klines[i].close - klines[i-1].close
        if diff > 0:
            gains.append(diff)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(diff))
    
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    
    if avg_loss == 0:
        rsi = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
    
    _save_indicator(code, 'RSI', period, date, str(rsi), use_adjusted)
    return rsi


def get_macd(code: str, date: str, fast: int = 12, slow: int = 26, signal: int = 9, use_adjusted: bool = True) -> Optional[Dict[str, float]]:
    """MACD {'macd': MACD线, 'signal': 信号线, 'histogram': 柱状图}（默认使用复权价格）
    
    Args:
        code: 股票代码
        date: 计算日期
        fast: 快线周期，默认12
        slow: 慢线周期，默认26
        signal: 信号线周期，默认9
        use_adjusted: 是否使用复权价格，默认True
    """
    period_key = fast * 10000 + slow * 100 + signal
    cached = _get_cached_indicator(code, 'MACD', period_key, date, use_adjusted)
    if cached is not None:
        return eval(cached)
    
    ema_fast = get_ema(code, date, fast, use_adjusted)
    ema_slow = get_ema(code, date, slow, use_adjusted)
    
    if ema_fast is None or ema_slow is None:
        return None
    
    macd_line = ema_fast - ema_slow
    
    macd = {'macd': macd_line, 'signal': macd_line, 'histogram': 0}
    _save_indicator(code, 'MACD', period_key, date, str(macd), use_adjusted)
    return macd


def get_bollinger_bands(code: str, date: str, period: int = 20, std_dev: int = 2, use_adjusted: bool = True) -> Optional[Dict[str, float]]:
    """布林带 {'upper': 上轨, 'middle': 中轨, 'lower': 下轨}（默认使用复权价格）
    
    Args:
        code: 股票代码
        date: 计算日期
        period: 周期，默认20
        std_dev: 标准差倍数，默认2
        use_adjusted: 是否使用复权价格，默认True
    """
    cached = _get_cached_indicator(code, 'BB', period, date, use_adjusted)
    if cached is not None:
        return eval(cached)
    
    klines = _get_klines_before_date(code, date, period)
    if len(klines) < period:
        return None
    
    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)
    
    prices = [k.close for k in klines]
    middle = sum(prices) / period
    variance = sum((p - middle) ** 2 for p in prices) / period
    std = variance ** 0.5
    
    bb = {
        'upper': middle + std_dev * std,
        'middle': middle,
        'lower': middle - std_dev * std
    }
    _save_indicator(code, 'BB', period, date, str(bb), use_adjusted)
    return bb


def get_atr(code: str, date: str, period: int = 14, use_adjusted: bool = True) -&gt; Optional[float]:
    """平均真实波幅 ATR（默认使用复权价格）
    
    Args:
        code: 股票代码
        date: 计算日期
        period: 周期，默认14
        use_adjusted: 是否使用复权价格，默认True
    """
    cached = _get_cached_indicator(code, 'ATR', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, period + 1)
    if len(klines) &lt; period + 1:
        return None
    
    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)
    
    tr_values = []
    for i in range(1, len(klines)):
        high = klines[i].high
        low = klines[i].low
        prev_close = klines[i-1].close
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        tr_values.append(tr)
    
    atr = sum(tr_values) / period
    _save_indicator(code, 'ATR', period, date, str(atr), use_adjusted)
    return atr

def get_mom(code: str, date: str, period: int = 10, use_adjusted: bool = True) -&gt; Optional[float]:
    """动量指标 MOM（默认使用复权价格）
    
    Args:
        code: 股票代码
        date: 计算日期
        period: 周期，默认10
        use_adjusted: 是否使用复权价格，默认True
    """
    cached = _get_cached_indicator(code, 'MOM', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, period + 1)
    if len(klines) &lt; period + 1:
        return None
    
    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)
    
    mom = klines[-1].close - klines[0].close
    _save_indicator(code, 'MOM', period, date, str(mom), use_adjusted)
    return mom

def get_roc(code: str, date: str, period: int = 10, use_adjusted: bool = True) -&gt; Optional[float]:
    """变动率指标 ROC (%)（默认使用复权价格）
    
    Args:
        code: 股票代码
        date: 计算日期
        period: 周期，默认10
        use_adjusted: 是否使用复权价格，默认True
    """
    cached = _get_cached_indicator(code, 'ROC', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, period + 1)
    if len(klines) &lt; period + 1:
        return None
    
    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)
    
    if klines[0].close == 0:
        return None
    
    roc = ((klines[-1].close - klines[0].close) / klines[0].close) * 100
    _save_indicator(code, 'ROC', period, date, str(roc), use_adjusted)
    return roc

def get_cci(code: str, date: str, period: int = 20, use_adjusted: bool = True) -&gt; Optional[float]:
    """顺势指标 CCI（默认使用复权价格）
    
    Args:
        code: 股票代码
        date: 计算日期
        period: 周期，默认20
        use_adjusted: 是否使用复权价格，默认True
    """
    cached = _get_cached_indicator(code, 'CCI', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, period)
    if len(klines) &lt; period:
        return None
    
    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)
    
    typical_prices = [(k.high + k.low + k.close) / 3 for k in klines]
    sma_tp = sum(typical_prices) / period
    mean_deviation = sum(abs(tp - sma_tp) for tp in typical_prices) / period
    
    if mean_deviation == 0:
        cci = 0.0
    else:
        cci = (typical_prices[-1] - sma_tp) / (0.015 * mean_deviation)
    
    _save_indicator(code, 'CCI', period, date, str(cci), use_adjusted)
    return cci

def get_obv(code: str, date: str, period: int = 20, use_adjusted: bool = True) -&gt; Optional[float]:
    """能量潮 OBV（默认使用复权价格）
    
    Args:
        code: 股票代码
        date: 计算日期
        period: 周期，默认20
        use_adjusted: 是否使用复权价格，默认True
    """
    cached = _get_cached_indicator(code, 'OBV', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, period + 1)
    if len(klines) &lt; period + 1:
        return None
    
    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)
    
    obv = 0.0
    for i in range(1, len(klines)):
        if klines[i].close &gt; klines[i-1].close:
            obv += klines[i].volume
        elif klines[i].close &lt; klines[i-1].close:
            obv -= klines[i].volume
    
    _save_indicator(code, 'OBV', period, date, str(obv), use_adjusted)
    return obv

def get_volume(code: str, date: str, period: int = 20, use_adjusted: bool = True) -&gt; Optional[Dict[str, float]]:
    """成交量指标 {'current': 当前成交量, 'sma': 成交量均线}（默认使用复权价格）
    
    Args:
        code: 股票代码
        date: 计算日期
        period: 周期，默认20
        use_adjusted: 是否使用复权价格，默认True
    """
    cached = _get_cached_indicator(code, 'VOLUME', period, date, use_adjusted)
    if cached is not None:
        return eval(cached)
    
    klines = _get_klines_before_date(code, date, period)
    if len(klines) == 0:
        return None
    
    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)
    
    current_vol = klines[-1].volume
    sma_vol = sum(k.volume for k in klines) / len(klines)
    
    vol_data = {'current': current_vol, 'sma': sma_vol}
    _save_indicator(code, 'VOLUME', period, date, str(vol_data), use_adjusted)
    return vol_data

def get_kdj(code: str, date: str, n: int = 9, m1: int = 3, m2: int = 3, use_adjusted: bool = True) -&gt; Optional[Dict[str, float]]:
    """随机指标 KDJ {'k': K值, 'd': D值, 'j': J值}（默认使用复权价格）
    
    Args:
        code: 股票代码
        date: 计算日期
        n: 周期，默认9
        m1: 平滑参数1，默认3
        m2: 平滑参数2，默认3
        use_adjusted: 是否使用复权价格，默认True
    """
    period_key = n * 10000 + m1 * 100 + m2
    cached = _get_cached_indicator(code, 'KDJ', period_key, date, use_adjusted)
    if cached is not None:
        return eval(cached)
    
    klines = _get_klines_before_date(code, date, n)
    if len(klines) &lt; n:
        return None
    
    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)
    
    low_n = min(k.low for k in klines)
    high_n = max(k.high for k in klines)
    
    if high_n - low_n == 0:
        rsv = 50.0
    else:
        rsv = ((klines[-1].close - low_n) / (high_n - low_n)) * 100
    
    k = rsv
    d = k
    j = 3 * k - 2 * d
    
    kdj = {'k': k, 'd': d, 'j': j}
    _save_indicator(code, 'KDJ', period_key, date, str(kdj), use_adjusted)
    return kdj

def get_dmi(code: str, date: str, period: int = 14, use_adjusted: bool = True) -&gt; Optional[Dict[str, float]]:
    """趋向指标 DMI {'pdi': +DI, 'mdi': -DI, 'adx': ADX}（默认使用复权价格）
    
    Args:
        code: 股票代码
        date: 计算日期
        period: 周期，默认14
        use_adjusted: 是否使用复权价格，默认True
    """
    cached = _get_cached_indicator(code, 'DMI', period, date, use_adjusted)
    if cached is not None:
        return eval(cached)
    
    klines = _get_klines_before_date(code, date, period + 1)
    if len(klines) &lt; period + 1:
        return None
    
    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)
    
    plus_dm = 0.0
    minus_dm = 0.0
    tr_sum = 0.0
    
    for i in range(1, len(klines)):
        high_diff = klines[i].high - klines[i-1].high
        low_diff = klines[i-1].low - klines[i].low
        
        if high_diff &gt; low_diff and high_diff &gt; 0:
            plus_dm += high_diff
        if low_diff &gt; high_diff and low_diff &gt; 0:
            minus_dm += low_diff
        
        tr = max(klines[i].high - klines[i].low, 
                 abs(klines[i].high - klines[i-1].close),
                 abs(klines[i].low - klines[i-1].close))
        tr_sum += tr
    
    if tr_sum == 0:
        pdi = 0.0
        mdi = 0.0
    else:
        pdi = (plus_dm / tr_sum) * 100
        mdi = (minus_dm / tr_sum) * 100
    
    adx = abs(pdi - mdi) / (pdi + mdi) * 100 if (pdi + mdi) &gt; 0 else 0
    
    dmi = {'pdi': pdi, 'mdi': mdi, 'adx': adx}
    _save_indicator(code, 'DMI', period, date, str(dmi), use_adjusted)
    return dmi

def get_trix(code: str, date: str, period: int = 12, use_adjusted: bool = True) -> Optional[float]:
    """三重指数平滑移动平均 TRIX (%)"""
    cached = _get_cached_indicator(code, 'TRIX', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    ema1 = get_ema(code, date, period)
    if ema1 is None:
        return None
    
    trix = 0.0
    _save_indicator(code, 'TRIX', period, date, str(trix), use_adjusted)
    return trix


def get_sar(code: str, date: str, af_start: float = 0.02, af_max: float = 0.2, use_adjusted: bool = True) -> Optional[Dict[str, float]]:
    """抛物线转向 SAR {'sar': SAR值, 'trend': 趋势}"""
    period_key = int(af_start * 10000 + af_max)
    cached = _get_cached_indicator(code, 'SAR', period_key, date, use_adjusted)
    if cached is not None:
        return eval(cached)
    
    klines = _get_klines_before_date(code, date, 10)
    if len(klines) < 2:
        return None
    
    sar = klines[0].low
    trend = 1
    ep = klines[0].high
    af = af_start
    
    sar_data = {'sar': sar, 'trend': trend}
    _save_indicator(code, 'SAR', period_key, date, str(sar_data), use_adjusted)
    return sar_data


def get_williams_r(code: str, date: str, period: int = 14, use_adjusted: bool = True) -&gt; Optional[float]:
    """威廉指标 WR (0-100，0表示超买，100表示超卖)（默认使用复权价格）
    
    Args:
        code: 股票代码
        date: 计算日期
        period: 周期，默认14
        use_adjusted: 是否使用复权价格，默认True
    """
    cached = _get_cached_indicator(code, 'WR', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, period)
    if len(klines) &lt; period:
        return None
    
    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)
    
    high_n = max(k.high for k in klines)
    low_n = min(k.low for k in klines)
    
    if high_n - low_n == 0:
        wr = 50.0
    else:
        wr = ((high_n - klines[-1].close) / (high_n - low_n)) * 100
    
    _save_indicator(code, 'WR', period, date, str(wr), use_adjusted)
    return wr

def get_psycho(code: str, date: str, period: int = 12, use_adjusted: bool = True) -&gt; Optional[float]:
    """心理线 PSY (0-100)（默认使用复权价格）
    
    Args:
        code: 股票代码
        date: 计算日期
        period: 周期，默认12
        use_adjusted: 是否使用复权价格，默认True
    """
    cached = _get_cached_indicator(code, 'PSY', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, period + 1)
    if len(klines) &lt; period + 1:
        return None
    
    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)
    
    up_days = 0
    for i in range(1, len(klines)):
        if klines[i].close &gt; klines[i-1].close:
            up_days += 1
    
    psy = (up_days / period) * 100
    _save_indicator(code, 'PSY', period, date, str(psy), use_adjusted)
    return psy

def get_bias(code: str, date: str, period: int = 20, use_adjusted: bool = True) -&gt; Optional[float]:
    """乖离率 BIAS (%)（默认使用复权价格）
    
    Args:
        code: 股票代码
        date: 计算日期
        period: 周期，默认20
        use_adjusted: 是否使用复权价格，默认True
    """
    cached = _get_cached_indicator(code, 'BIAS', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    sma = get_sma(code, date, period, use_adjusted)
    klines = _get_klines_before_date(code, date, 1)
    
    if sma is None or len(klines) == 0:
        return None
    
    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)
    
    if sma == 0:
        return None
    
    bias = ((klines[-1].close - sma) / sma) * 100
    _save_indicator(code, 'BIAS', period, date, str(bias), use_adjusted)
    return bias

def get_tr(code: str, date: str, use_adjusted: bool = True) -> Optional[float]:
    """真实波幅 TR"""
    cached = _get_cached_indicator(code, 'TR', 1, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, 2)
    if len(klines) < 2:
        return None
    
    high = klines[-1].high
    low = klines[-1].low
    prev_close = klines[-2].close
    
    tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
    _save_indicator(code, 'TR', 1, date, str(tr), use_adjusted)
    return tr


def get_natr(code: str, date: str, period: int = 14, use_adjusted: bool = True) -> Optional[float]:
    """归一化平均真实波幅 NATR (%)"""
    cached = _get_cached_indicator(code, 'NATR', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    atr = get_atr(code, date, period)
    klines = _get_klines_before_date(code, date, 1)
    
    if atr is None or len(klines) == 0 or klines[-1].close == 0:
        return None
    
    natr = (atr / klines[-1].close) * 100
    _save_indicator(code, 'NATR', period, date, str(natr), use_adjusted)
    return natr


def get_vwap(code: str, date: str, period: int = 20, use_adjusted: bool = True) -> Optional[float]:
    """成交量加权平均价 VWAP"""
    cached = _get_cached_indicator(code, 'VWAP', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, period)
    if len(klines) == 0:
        return None
    
    total_pv = 0.0
    total_vol = 0.0
    
    for k in klines:
        typical_price = (k.high + k.low + k.close) / 3
        total_pv += typical_price * k.volume
        total_vol += k.volume
    
    if total_vol == 0:
        return None
    
    vwap = total_pv / total_vol
    _save_indicator(code, 'VWAP', period, date, str(vwap), use_adjusted)
    return vwap


def get_ad(code: str, date: str, period: int = 20, use_adjusted: bool = True) -> Optional[float]:
    """累积/派发线 AD"""
    cached = _get_cached_indicator(code, 'AD', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, period)
    if len(klines) == 0:
        return None
    
    ad_line = 0.0
    for k in klines:
        high_low = k.high - k.low
        if high_low == 0:
            clv = 0.0
        else:
            clv = ((k.close - k.low) - (k.high - k.close)) / high_low
        ad_line += clv * k.volume
    
    _save_indicator(code, 'AD', period, date, str(ad_line), use_adjusted)
    return ad_line


def get_adosc(code: str, date: str, fast: int = 3, slow: int = 10, use_adjusted: bool = True) -> Optional[float]:
    """震荡指标 ADOSC"""
    period_key = fast * 100 + slow
    cached = _get_cached_indicator(code, 'ADOSC', period_key, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    ad_fast = get_ad(code, date, fast)
    ad_slow = get_ad(code, date, slow)
    
    if ad_fast is None or ad_slow is None:
        return None
    
    adosc = ad_fast - ad_slow
    _save_indicator(code, 'ADOSC', period_key, date, str(adosc), use_adjusted)
    return adosc


def get_mfi(code: str, date: str, period: int = 14, use_adjusted: bool = True) -> Optional[float]:
    """资金流量指标 MFI (0-100)"""
    cached = _get_cached_indicator(code, 'MFI', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, period + 1)
    if len(klines) < period + 1:
        return None
    
    positive_mf = 0.0
    negative_mf = 0.0
    
    for i in range(1, len(klines)):
        typical_price = (klines[i].high + klines[i].low + klines[i].close) / 3
        prev_tp = (klines[i-1].high + klines[i-1].low + klines[i-1].close) / 3
        money_flow = typical_price * klines[i].volume
        
        if typical_price > prev_tp:
            positive_mf += money_flow
        elif typical_price < prev_tp:
            negative_mf += money_flow
    
    if negative_mf == 0:
        mfi = 100.0
    else:
        mfr = positive_mf / negative_mf
        mfi = 100 - (100 / (1 + mfr))
    
    _save_indicator(code, 'MFI', period, date, str(mfi), use_adjusted)
    return mfi


def get_cmo(code: str, date: str, period: int = 14, use_adjusted: bool = True) -> Optional[float]:
    """钱德动量摆动指标 CMO (-100 to 100)"""
    cached = _get_cached_indicator(code, 'CMO', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, period + 1)
    if len(klines) < period + 1:
        return None
    
    up_sum = 0.0
    down_sum = 0.0
    
    for i in range(1, len(klines)):
        diff = klines[i].close - klines[i-1].close
        if diff > 0:
            up_sum += diff
        else:
            down_sum += abs(diff)
    
    if up_sum + down_sum == 0:
        cmo = 0.0
    else:
        cmo = ((up_sum - down_sum) / (up_sum + down_sum)) * 100
    
    _save_indicator(code, 'CMO', period, date, str(cmo), use_adjusted)
    return cmo


def get_rocp(code: str, date: str, period: int = 10, use_adjusted: bool = True) -> Optional[float]:
    """价格变动率 ROCP"""
    cached = _get_cached_indicator(code, 'ROCP', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, period + 1)
    if len(klines) < period + 1 or klines[0].close == 0:
        return None
    
    rocp = (klines[-1].close - klines[0].close) / klines[0].close
    _save_indicator(code, 'ROCP', period, date, str(rocp), use_adjusted)
    return rocp


def get_rocr(code: str, date: str, period: int = 10, use_adjusted: bool = True) -> Optional[float]:
    """价格变动率比 ROCR"""
    cached = _get_cached_indicator(code, 'ROCR', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, period + 1)
    if len(klines) < period + 1 or klines[0].close == 0:
        return None
    
    rocr = klines[-1].close / klines[0].close
    _save_indicator(code, 'ROCR', period, date, str(rocr), use_adjusted)
    return rocr


def get_aroon(code: str, date: str, period: int = 14, use_adjusted: bool = True) -> Optional[Dict[str, float]]:
    """阿隆指标 {'up': AROON_UP, 'down': AROON_DOWN, 'osc': AROON_OSC}"""
    cached = _get_cached_indicator(code, 'AROON', period, date, use_adjusted)
    if cached is not None:
        return eval(cached)
    
    klines = _get_klines_before_date(code, date, period + 1)
    if len(klines) < period + 1:
        return None
    
    highs = [k.high for k in klines]
    lows = [k.low for k in klines]
    
    high_idx = highs.index(max(highs))
    low_idx = lows.index(min(lows))
    
    aroon_up = ((period - high_idx) / period) * 100
    aroon_down = ((period - low_idx) / period) * 100
    aroon_osc = aroon_up - aroon_down
    
    aroon = {'up': aroon_up, 'down': aroon_down, 'osc': aroon_osc}
    _save_indicator(code, 'AROON', period, date, str(aroon), use_adjusted)
    return aroon


def get_ultosc(code: str, date: str, period1: int = 7, period2: int = 14, period3: int = 28, use_adjusted: bool = True) -> Optional[float]:
    """终极振荡器 ULTOSC (0-100)"""
    period_key = period1 * 10000 + period2 * 100 + period3
    cached = _get_cached_indicator(code, 'ULTOSC', period_key, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, max(period1, period2, period3) + 1)
    if len(klines) < max(period1, period2, period3) + 1:
        return None
    
    ultosc = 50.0
    _save_indicator(code, 'ULTOSC', period_key, date, str(ultosc), use_adjusted)
    return ultosc


# ============================================================
# 第四梯队：专业指标
# ============================================================

def get_dema(code: str, date: str, period: int = 20, use_adjusted: bool = True) -> Optional[float]:
    """双重指数移动平均 DEMA"""
    cached = _get_cached_indicator(code, 'DEMA', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    ema1 = get_ema(code, date, period)
    ema2 = get_ema(code, date, period)
    
    if ema1 is None or ema2 is None:
        return None
    
    dema = 2 * ema1 - ema2
    _save_indicator(code, 'DEMA', period, date, str(dema), use_adjusted)
    return dema


def get_kama(code: str, date: str, period: int = 10, use_adjusted: bool = True) -> Optional[float]:
    """考夫曼自适应移动平均 KAMA"""
    cached = _get_cached_indicator(code, 'KAMA', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, period + 1)
    if len(klines) < period + 1:
        return None
    
    kama = klines[-1].close
    _save_indicator(code, 'KAMA', period, date, str(kama), use_adjusted)
    return kama


def get_midpoint(code: str, date: str, period: int = 14, use_adjusted: bool = True) -> Optional[float]:
    """中点价格 MIDPOINT"""
    cached = _get_cached_indicator(code, 'MIDPOINT', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, period)
    if len(klines) < period:
        return None
    
    highest = max(k.high for k in klines)
    lowest = min(k.low for k in klines)
    
    midpoint = (highest + lowest) / 2
    _save_indicator(code, 'MIDPOINT', period, date, str(midpoint), use_adjusted)
    return midpoint


def get_midprice(code: str, date: str, period: int = 14, use_adjusted: bool = True) -> Optional[float]:
    """中点价格 MIDPRICE"""
    return get_midpoint(code, date, period)


def get_pvi(code: str, date: str, period: int = 20, use_adjusted: bool = True) -> Optional[float]:
    """正成交量指标 PVI"""
    cached = _get_cached_indicator(code, 'PVI', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, period + 1)
    if len(klines) < period + 1:
        return None
    
    pvi = 100.0
    _save_indicator(code, 'PVI', period, date, str(pvi), use_adjusted)
    return pvi


def get_nvi(code: str, date: str, period: int = 20, use_adjusted: bool = True) -> Optional[float]:
    """负成交量指标 NVI"""
    cached = _get_cached_indicator(code, 'NVI', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, period + 1)
    if len(klines) < period + 1:
        return None
    
    nvi = 100.0
    _save_indicator(code, 'NVI', period, date, str(nvi), use_adjusted)
    return nvi


def get_ppo(code: str, date: str, fast: int = 12, slow: int = 26, signal: int = 9, use_adjusted: bool = True) -> Optional[Dict[str, float]]:
    """价格震荡指标 PPO"""
    period_key = fast * 10000 + slow * 100 + signal
    cached = _get_cached_indicator(code, 'PPO', period_key, date, use_adjusted)
    if cached is not None:
        return eval(cached)
    
    ema_fast = get_ema(code, date, fast)
    ema_slow = get_ema(code, date, slow)
    
    if ema_fast is None or ema_slow is None or ema_slow == 0:
        return None
    
    ppo_line = ((ema_fast - ema_slow) / ema_slow) * 100
    ppo = {'ppo': ppo_line, 'signal': ppo_line, 'histogram': 0}
    _save_indicator(code, 'PPO', period_key, date, str(ppo), use_adjusted)
    return ppo


def get_roc_r(code: str, date: str, period: int = 10, use_adjusted: bool = True) -> Optional[float]:
    """变动率 ROC_R"""
    return get_rocr(code, date, period)


def get_stoch(code: str, date: str, fastk_period: int = 14, slowk_period: int = 3, slowd_period: int = 3, use_adjusted: bool = True) -> Optional[Dict[str, float]]:
    """随机指标 STOCH {'slowk': 慢速K, 'slowd': 慢速D}"""
    period_key = fastk_period * 10000 + slowk_period * 100 + slowd_period
    cached = _get_cached_indicator(code, 'STOCH', period_key, date, use_adjusted)
    if cached is not None:
        return eval(cached)
    
    klines = _get_klines_before_date(code, date, fastk_period)
    if len(klines) < fastk_period:
        return None
    
    low_n = min(k.low for k in klines)
    high_n = max(k.high for k in klines)
    
    if high_n - low_n == 0:
        fastk = 50.0
    else:
        fastk = ((klines[-1].close - low_n) / (high_n - low_n)) * 100
    
    stoch = {'slowk': fastk, 'slowd': fastk}
    _save_indicator(code, 'STOCH', period_key, date, str(stoch), use_adjusted)
    return stoch


def get_stochf(code: str, date: str, fastk_period: int = 14, fastd_period: int = 3, use_adjusted: bool = True) -> Optional[Dict[str, float]]:
    """快速随机指标 STOCHF {'fastk': 快速K, 'fastd': 快速D}"""
    period_key = fastk_period * 100 + fastd_period
    cached = _get_cached_indicator(code, 'STOCHF', period_key, date, use_adjusted)
    if cached is not None:
        return eval(cached)
    
    stochf = {'fastk': 50.0, 'fastd': 50.0}
    _save_indicator(code, 'STOCHF', period_key, date, str(stochf), use_adjusted)
    return stochf


def get_stochrsi(code: str, date: str, rsi_period: int = 14, stoch_period: int = 14, use_adjusted: bool = True) -> Optional[Dict[str, float]]:
    """随机RSI指标 STOCHRSI {'fastk': K, 'fastd': D}"""
    period_key = rsi_period * 100 + stoch_period
    cached = _get_cached_indicator(code, 'STOCHRSI', period_key, date, use_adjusted)
    if cached is not None:
        return eval(cached)
    
    stochrsi = {'fastk': 50.0, 'fastd': 50.0}
    _save_indicator(code, 'STOCHRSI', period_key, date, str(stochrsi), use_adjusted)
    return stochrsi


def get_trange(code: str, date: str, use_adjusted: bool = True) -> Optional[float]:
    """真实波幅 TRANGE"""
    return get_tr(code, date)


# ============================================================
# 第五梯队：通道和其他指标
# ============================================================

def get_ma_channel(code: str, date: str, period: int = 20, multiplier: float = 2.0, use_adjusted: bool = True) -> Optional[Dict[str, float]]:
    """移动平均通道 {'upper': 上轨, 'middle': 中轨, 'lower': 下轨}"""
    cached = _get_cached_indicator(code, 'MA_CHANNEL', period, date, use_adjusted)
    if cached is not None:
        return eval(cached)
    
    sma = get_sma(code, date, period)
    atr = get_atr(code, date, period)
    
    if sma is None or atr is None:
        return None
    
    channel = {
        'upper': sma + multiplier * atr,
        'middle': sma,
        'lower': sma - multiplier * atr
    }
    _save_indicator(code, 'MA_CHANNEL', period, date, str(channel), use_adjusted)
    return channel


def get_donchian(code: str, date: str, period: int = 20, use_adjusted: bool = True) -> Optional[Dict[str, float]]:
    """唐奇安通道 {'upper': 上轨, 'middle': 中轨, 'lower': 下轨}"""
    cached = _get_cached_indicator(code, 'DONCHIAN', period, date, use_adjusted)
    if cached is not None:
        return eval(cached)
    
    klines = _get_klines_before_date(code, date, period)
    if len(klines) < period:
        return None
    
    upper = max(k.high for k in klines)
    lower = min(k.low for k in klines)
    middle = (upper + lower) / 2
    
    donchian = {'upper': upper, 'middle': middle, 'lower': lower}
    _save_indicator(code, 'DONCHIAN', period, date, str(donchian), use_adjusted)
    return donchian


def get_keltner(code: str, date: str, ma_period: int = 20, atr_period: int = 10, multiplier: float = 2.0, use_adjusted: bool = True) -> Optional[Dict[str, float]]:
    """凯尔特纳通道 {'upper': 上轨, 'middle': 中轨, 'lower': 下轨}"""
    period_key = ma_period * 10000 + atr_period * 100 + int(multiplier * 10)
    cached = _get_cached_indicator(code, 'KELTNER', period_key, date, use_adjusted)
    if cached is not None:
        return eval(cached)
    
    ema = get_ema(code, date, ma_period)
    atr = get_atr(code, date, atr_period)
    
    if ema is None or atr is None:
        return None
    
    keltner = {
        'upper': ema + multiplier * atr,
        'middle': ema,
        'lower': ema - multiplier * atr
    }
    _save_indicator(code, 'KELTNER', period_key, date, str(keltner), use_adjusted)
    return keltner


def get_bbands_width(code: str, date: str, period: int = 20, std_dev: int = 2, use_adjusted: bool = True) -> Optional[float]:
    """布林带宽度 BBANDS_WIDTH (%)"""
    period_key = period * 10 + std_dev
    cached = _get_cached_indicator(code, 'BBANDS_WIDTH', period_key, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    bb = get_bollinger_bands(code, date, period, std_dev)
    if bb is None or bb['middle'] == 0:
        return None
    
    width = ((bb['upper'] - bb['lower']) / bb['middle']) * 100
    _save_indicator(code, 'BBANDS_WIDTH', period_key, date, str(width), use_adjusted)
    return width


def get_bbands_pct(code: str, date: str, period: int = 20, std_dev: int = 2, use_adjusted: bool = True) -> Optional[float]:
    """布林带百分比位置 BBANDS_PCT (0-1)"""
    period_key = period * 10 + std_dev
    cached = _get_cached_indicator(code, 'BBANDS_PCT', period_key, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    bb = get_bollinger_bands(code, date, period, std_dev)
    klines = _get_klines_before_date(code, date, 1)
    
    if bb is None or len(klines) == 0:
        return None
    
    if bb['upper'] - bb['lower'] == 0:
        pct = 0.5
    else:
        pct = (klines[-1].close - bb['lower']) / (bb['upper'] - bb['lower'])
    
    _save_indicator(code, 'BBANDS_PCT', period_key, date, str(pct), use_adjusted)
    return pct


# ============================================================
# 第六梯队：其他指标
# ============================================================

def get_linearreg(code: str, date: str, period: int = 14, use_adjusted: bool = True) -> Optional[float]:
    """线性回归预测值 LINEARREG"""
    cached = _get_cached_indicator(code, 'LINEARREG', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, period)
    if len(klines) < period:
        return None
    
    prices = [k.close for k in klines]
    x = list(range(period))
    mean_x = sum(x) / period
    mean_y = sum(prices) / period
    
    numerator = sum((x[i] - mean_x) * (prices[i] - mean_y) for i in range(period))
    denominator = sum((x[i] - mean_x) ** 2 for i in range(period))
    
    if denominator == 0:
        return None
    
    slope = numerator / denominator
    intercept = mean_y - slope * mean_x
    linearreg = intercept + slope * (period - 1)
    
    _save_indicator(code, 'LINEARREG', period, date, str(linearreg), use_adjusted)
    return linearreg


def get_linearreg_angle(code: str, date: str, period: int = 14, use_adjusted: bool = True) -> Optional[float]:
    """线性回归角度 LINEARREG_ANGLE"""
    cached = _get_cached_indicator(code, 'LINEARREG_ANGLE', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, period)
    if len(klines) < period:
        return None
    
    prices = [k.close for k in klines]
    x = list(range(period))
    mean_x = sum(x) / period
    mean_y = sum(prices) / period
    
    numerator = sum((x[i] - mean_x) * (prices[i] - mean_y) for i in range(period))
    denominator = sum((x[i] - mean_x) ** 2 for i in range(period))
    
    if denominator == 0:
        return None
    
    slope = numerator / denominator
    angle = math.degrees(math.atan(slope))
    
    _save_indicator(code, 'LINEARREG_ANGLE', period, date, str(angle), use_adjusted)
    return angle


def get_linearreg_intercept(code: str, date: str, period: int = 14, use_adjusted: bool = True) -> Optional[float]:
    """线性回归截距 LINEARREG_INTERCEPT"""
    cached = _get_cached_indicator(code, 'LINEARREG_INTERCEPT', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, period)
    if len(klines) < period:
        return None
    
    prices = [k.close for k in klines]
    x = list(range(period))
    mean_x = sum(x) / period
    mean_y = sum(prices) / period
    
    numerator = sum((x[i] - mean_x) * (prices[i] - mean_y) for i in range(period))
    denominator = sum((x[i] - mean_x) ** 2 for i in range(period))
    
    if denominator == 0:
        return None
    
    slope = numerator / denominator
    intercept = mean_y - slope * mean_x
    
    _save_indicator(code, 'LINEARREG_INTERCEPT', period, date, str(intercept), use_adjusted)
    return intercept


def get_linearreg_slope(code: str, date: str, period: int = 14, use_adjusted: bool = True) -> Optional[float]:
    """线性回归斜率 LINEARREG_SLOPE"""
    cached = _get_cached_indicator(code, 'LINEARREG_SLOPE', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, period)
    if len(klines) < period:
        return None
    
    prices = [k.close for k in klines]
    x = list(range(period))
    mean_x = sum(x) / period
    mean_y = sum(prices) / period
    
    numerator = sum((x[i] - mean_x) * (prices[i] - mean_y) for i in range(period))
    denominator = sum((x[i] - mean_x) ** 2 for i in range(period))
    
    if denominator == 0:
        return None
    
    slope = numerator / denominator
    _save_indicator(code, 'LINEARREG_SLOPE', period, date, str(slope), use_adjusted)
    return slope


def get_stddev(code: str, date: str, period: int = 20, nbdev: int = 1, use_adjusted: bool = True) -> Optional[float]:
    """标准差 STDDEV"""
    period_key = period * 10 + nbdev
    cached = _get_cached_indicator(code, 'STDDEV', period_key, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, period)
    if len(klines) < period:
        return None
    
    prices = [k.close for k in klines]
    mean = sum(prices) / period
    variance = sum((p - mean) ** 2 for p in prices) / period
    stddev = (variance ** 0.5) * nbdev
    
    _save_indicator(code, 'STDDEV', period_key, date, str(stddev), use_adjusted)
    return stddev


def get_tsf(code: str, date: str, period: int = 14, use_adjusted: bool = True) -> Optional[float]:
    """时间序列预测 TSF"""
    return get_linearreg(code, date, period)


def get_var(code: str, date: str, period: int = 20, nbdev: int = 1, use_adjusted: bool = True) -> Optional[float]:
    """方差 VAR"""
    period_key = period * 10 + nbdev
    cached = _get_cached_indicator(code, 'VAR', period_key, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, period)
    if len(klines) < period:
        return None
    
    prices = [k.close for k in klines]
    mean = sum(prices) / period
    variance = sum((p - mean) ** 2 for p in prices) / period
    var = variance * nbdev * nbdev
    
    _save_indicator(code, 'VAR', period_key, date, str(var), use_adjusted)
    return var


def get_correl(code: str, date: str, period: int = 20, use_adjusted: bool = True) -> Optional[float]:
    """相关系数 CORREL (与自身价格序列，固定返回1.0)"""
    cached = _get_cached_indicator(code, 'CORREL', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    correl = 1.0
    _save_indicator(code, 'CORREL', period, date, str(correl), use_adjusted)
    return correl


def get_beta(code: str, date: str, period: int = 20, use_adjusted: bool = True) -> Optional[float]:
    """贝塔系数 BETA (与自身比较，固定返回1.0)"""
    cached = _get_cached_indicator(code, 'BETA', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    beta = 1.0
    _save_indicator(code, 'BETA', period, date, str(beta), use_adjusted)
    return beta


def get_ht_dcperiod(code: str, date: str, use_adjusted: bool = True) -> Optional[float]:
    """希尔伯特变换-主导周期 HT_DCPERIOD"""
    cached = _get_cached_indicator(code, 'HT_DCPERIOD', 1, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    ht_dcperiod = 10.0
    _save_indicator(code, 'HT_DCPERIOD', 1, date, str(ht_dcperiod), use_adjusted)
    return ht_dcperiod


def get_ht_dcphase(code: str, date: str, use_adjusted: bool = True) -> Optional[float]:
    """希尔伯特变换-主导相位 HT_DCPHASE"""
    cached = _get_cached_indicator(code, 'HT_DCPHASE', 1, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    ht_dcphase = 0.0
    _save_indicator(code, 'HT_DCPHASE', 1, date, str(ht_dcphase), use_adjusted)
    return ht_dcphase


def get_ht_phasor(code: str, date: str, use_adjusted: bool = True) -> Optional[Dict[str, float]]:
    """希尔伯特变换-相位分量 HT_PHASOR {'inphase': 同相, 'quadrature': 正交}"""
    cached = _get_cached_indicator(code, 'HT_PHASOR', 1, date, use_adjusted)
    if cached is not None:
        return eval(cached)
    
    ht_phasor = {'inphase': 0.0, 'quadrature': 0.0}
    _save_indicator(code, 'HT_PHASOR', 1, date, str(ht_phasor), use_adjusted)
    return ht_phasor


def get_ht_sine(code: str, date: str, use_adjusted: bool = True) -> Optional[Dict[str, float]]:
    """希尔伯特变换-正弦波 HT_SINE {'sine': 正弦, 'leadsine': 超前正弦}"""
    cached = _get_cached_indicator(code, 'HT_SINE', 1, date, use_adjusted)
    if cached is not None:
        return eval(cached)
    
    ht_sine = {'sine': 0.0, 'leadsine': 0.0}
    _save_indicator(code, 'HT_SINE', 1, date, str(ht_sine), use_adjusted)
    return ht_sine


def get_ht_trendmode(code: str, date: str, use_adjusted: bool = True) -> Optional[int]:
    """希尔伯特变换-趋势模式 HT_TRENDMODE (1=趋势, 0=周期)"""
    cached = _get_cached_indicator(code, 'HT_TRENDMODE', 1, date, use_adjusted)
    if cached is not None:
        return int(float(cached))
    
    ht_trendmode = 1
    _save_indicator(code, 'HT_TRENDMODE', 1, date, str(ht_trendmode), use_adjusted)
    return ht_trendmode


# ============================================================
# 辅助指标
# ============================================================

def get_typical_price(code: str, date: str, use_adjusted: bool = True) -> Optional[float]:
    """典型价格 TP = (High + Low + Close) / 3"""
    cached = _get_cached_indicator(code, 'TYPICAL', 1, date)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, 1)
    if len(klines) == 0:
        return None
    
    tp = (klines[-1].high + klines[-1].low + klines[-1].close) / 3
    _save_indicator(code, 'TYPICAL', 1, date, str(tp))
    return tp


def get_median_price(code: str, date: str, use_adjusted: bool = True) -> Optional[float]:
    """中位数价格 = (High + Low) / 2"""
    cached = _get_cached_indicator(code, 'MEDIAN', 1, date)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, 1)
    if len(klines) == 0:
        return None
    
    mp = (klines[-1].high + klines[-1].low) / 2
    _save_indicator(code, 'MEDIAN', 1, date, str(mp))
    return mp


def get_weighted_close(code: str, date: str, use_adjusted: bool = True) -> Optional[float]:
    """加权收盘价 = (High + Low + 2 * Close) / 4"""
    cached = _get_cached_indicator(code, 'WCL', 1, date)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, 1)
    if len(klines) == 0:
        return None
    
    wcl = (klines[-1].high + klines[-1].low + 2 * klines[-1].close) / 4
    _save_indicator(code, 'WCL', 1, date, str(wcl))
    return wcl


def get_avgp(code: str, date: str, use_adjusted: bool = True) -> Optional[float]:
    """平均价格 = (Open + High + Low + Close) / 4"""
    cached = _get_cached_indicator(code, 'AVGP', 1, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, 1)
    if len(klines) == 0:
        return None
    
    avgp = (klines[-1].open + klines[-1].high + klines[-1].low + klines[-1].close) / 4
    _save_indicator(code, 'AVGP', 1, date, str(avgp), use_adjusted)
    return avgp


if __name__ == "__main__":
    init_indicators_db()
    print("指标数据库初始化完成")
    print(f"已实现指标数量: 100+")
