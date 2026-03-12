"""
data_loader.py - 数据获取模块

功能：
1. K线数据获取
2. 股票基本信息获取

设计原则：
- 函数功能单一、最小粒度
- 负责从数据源获取原始数据
"""

from typing import List, Optional
from data_fetcher import query_daily_kline, query_stock_basic
from define import DailyKline, StockBasic


def get_kline(code: str, start_date: str, end_date: str) -> List[DailyKline]:
    """获取K线数据"""
    return query_daily_kline(codes=[code], start_date=start_date, end_date=end_date)


def get_close_prices(code: str, start_date: str, end_date: str) -> List[float]:
    """获取收盘价列表"""
    klines = get_kline(code, start_date, end_date)
    return [k.close for k in klines]


def get_dates(code: str, start_date: str, end_date: str) -> List[str]:
    """获取日期列表"""
    klines = get_kline(code, start_date, end_date)
    return [k.date for k in klines]


def get_open_prices(code: str, start_date: str, end_date: str) -> List[float]:
    """获取开盘价列表"""
    klines = get_kline(code, start_date, end_date)
    return [k.open for k in klines]


def get_high_prices(code: str, start_date: str, end_date: str) -> List[float]:
    """获取最高价列表"""
    klines = get_kline(code, start_date, end_date)
    return [k.high for k in klines]


def get_low_prices(code: str, start_date: str, end_date: str) -> List[float]:
    """获取最低价列表"""
    klines = get_kline(code, start_date, end_date)
    return [k.low for k in klines]


def get_volumes(code: str, start_date: str, end_date: str) -> List[float]:
    """获取成交量列表"""
    klines = get_kline(code, start_date, end_date)
    return [k.volume for k in klines]


def get_pct_chg(code: str, start_date: str, end_date: str) -> List[float]:
    """获取涨跌幅列表"""
    klines = get_kline(code, start_date, end_date)
    return [k.pctChg for k in klines]


def get_stock_info(code: str) -> Optional[StockBasic]:
    """获取股票基本信息"""
    stocks = query_stock_basic(code=code)
    return stocks[0] if stocks else None


def get_all_stocks(status: str = None) -> List[StockBasic]:
    """获取所有股票列表"""
    return query_stock_basic(status=status)


def get_stock_codes(status: str = '1') -> List[str]:
    """获取股票代码列表"""
    stocks = query_stock_basic(status=status)
    return [s.code for s in stocks]
