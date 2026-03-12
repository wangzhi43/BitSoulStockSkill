"""
indicators.py - 技术指标计算模块

功能：
1. 技术指标计算（SMA, EMA, RSI, MACD, BB, ATR等）
2. 计算结果缓存到数据库

设计原则：
- 函数功能单一、最小粒度
- 查询优先使用缓存，计算后存入数据库
"""

import sqlite3
from typing import Optional, Dict
from define import DB_PATH


def init_indicators_db():
    """初始化指标缓存表"""
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS cached_indicators (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                indicator_type TEXT NOT NULL,
                period INTEGER,
                date TEXT NOT NULL,
                value TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(code, indicator_type, period, date)
            );
            CREATE INDEX IF NOT EXISTS idx_indicators_lookup ON cached_indicators(code, indicator_type, period, date);
        """)
        conn.commit()
    finally:
        conn.close()


def _get_conn():
    return sqlite3.connect(DB_PATH)


def _get_cached_indicator(code: str, indicator_type: str, period: int, date: str) -> Optional[str]:
    """查询缓存指标"""
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "SELECT value FROM cached_indicators WHERE code=? AND indicator_type=? AND period=? AND date=?",
            (code, indicator_type, period, date)
        )
        row = cursor.fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def _save_indicator(code: str, indicator_type: str, period: int, date: str, value: str):
    """保存指标到缓存"""
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO cached_indicators (code, indicator_type, period, date, value) VALUES (?, ?, ?, ?, ?)",
            (code, indicator_type, period, date, value)
        )
        conn.commit()
    finally:
        conn.close()


def get_sma(code: str, date: str, period: int = 20) -> Optional[float]:
    """简单移动平均 SMA"""
    cached = _get_cached_indicator(code, 'SMA', period, date)
    if cached is not None:
        return float(cached)
    
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "SELECT close FROM daily_kline WHERE code=? AND date <= ? ORDER BY date DESC LIMIT ?",
            (code, date, period)
        )
        prices = [row[0] for row in cursor.fetchall()]
        if len(prices) < period:
            return None
        sma = sum(prices[:period]) / period
        _save_indicator(code, 'SMA', period, date, str(sma))
        return sma
    finally:
        conn.close()


def get_ema(code: str, date: str, period: int = 12) -> Optional[float]:
    """指数移动平均 EMA"""
    cached = _get_cached_indicator(code, 'EMA', period, date)
    if cached is not None:
        return float(cached)
    
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "SELECT close FROM daily_kline WHERE code=? AND date <= ? ORDER BY date ASC",
            (code, date)
        )
        prices = [row[0] for row in cursor.fetchall()]
        if len(prices) < period:
            return None
        ema = prices[0]
        multiplier = 2 / (period + 1)
        for price in prices[1:]:
            ema = (price - ema) * multiplier + ema
        _save_indicator(code, 'EMA', period, date, str(ema))
        return ema
    finally:
        conn.close()


def get_rsi(code: str, date: str, period: int = 14) -> Optional[float]:
    """相对强弱指标 RSI (0-100)"""
    cached = _get_cached_indicator(code, 'RSI', period, date)
    if cached is not None:
        return float(cached)
    
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "SELECT close FROM daily_kline WHERE code=? AND date <= ? ORDER BY date DESC LIMIT ?",
            (code, date, period + 1)
        )
        prices = [row[0] for row in cursor.fetchall()]
        if len(prices) < period + 1:
            return None
        
        prices = prices[:period + 1][::-1]
        gains, losses = [], []
        for i in range(1, len(prices)):
            diff = prices[i] - prices[i - 1]
            if diff > 0:
                gains.append(diff)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(diff))
        
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        
        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        
        _save_indicator(code, 'RSI', period, date, str(rsi))
        return rsi
    finally:
        conn.close()


def get_bollinger_bands(code: str, date: str, period: int = 20, std_dev: int = 2) -> Optional[Dict[str, float]]:
    """布林带 {'upper': 上轨, 'middle': 中轨, 'lower': 下轨}"""
    cached = _get_cached_indicator(code, 'BB', period, date)
    if cached is not None:
        return eval(cached)
    
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "SELECT close FROM daily_kline WHERE code=? AND date <= ? ORDER BY date DESC LIMIT ?",
            (code, date, period)
        )
        prices = [row[0] for row in cursor.fetchall()]
        if len(prices) < period:
            return None
        
        prices = prices[:period][::-1]
        middle = sum(prices) / period
        variance = sum((p - middle) ** 2 for p in prices) / period
        std = variance ** 0.5
        
        bb = {
            'upper': middle + std_dev * std,
            'middle': middle,
            'lower': middle - std_dev * std
        }
        _save_indicator(code, 'BB', period, date, str(bb))
        return bb
    finally:
        conn.close()


def get_macd(code: str, date: str, fast: int = 12, slow: int = 26, signal: int = 9) -> Optional[Dict[str, float]]:
    """MACD {'macd': MACD线, 'signal': 信号线, 'histogram': 柱状图}"""
    period_key = fast * 100 + slow
    cached = _get_cached_indicator(code, 'MACD', period_key, date)
    if cached is not None:
        return eval(cached)
    
    ema_fast = get_ema(code, date, fast)
    ema_slow = get_ema(code, date, slow)
    
    if ema_fast is None or ema_slow is None:
        return None
    
    macd_line = ema_fast - ema_slow
    macd = {'macd': macd_line, 'signal': 0, 'histogram': macd_line}
    _save_indicator(code, 'MACD', period_key, date, str(macd))
    return macd


def get_atr(code: str, date: str, period: int = 14) -> Optional[float]:
    """平均真实波幅 ATR"""
    cached = _get_cached_indicator(code, 'ATR', period, date)
    if cached is not None:
        return float(cached)
    
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "SELECT high, low, close FROM daily_kline WHERE code=? AND date <= ? ORDER BY date DESC LIMIT ?",
            (code, date, period + 1)
        )
        rows = cursor.fetchall()
        if len(rows) < period + 1:
            return None
        
        tr_values = []
        for i in range(len(rows) - 1):
            high, low, close = rows[i]
            prev_close = rows[i + 1][2]
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            tr_values.append(tr)
        
        atr = sum(tr_values) / period
        _save_indicator(code, 'ATR', period, date, str(atr))
        return atr
    finally:
        conn.close()


if __name__ == "__main__":
    init_indicators_db()
    print("指标数据库初始化完成")
