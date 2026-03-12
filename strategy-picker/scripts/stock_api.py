"""
stock_api.py — 股票基础数据接口（预定义）

策略逻辑可调用此模块中的所有函数来获取股票数据。
当前为模拟实现，真实环境中替换为实际数据源即可。
"""

import random
from datetime import date, timedelta
from typing import Optional, List

from data_fetcher import query_stock_basic, query_daily_kline
from define import DailyKline,StockBasic

class StockApi:
    # ─────────────────────────────────────────────
    # 股票基础信息类接口
    # ─────────────────────────────────────────────
    def get_all_symbols(self, status: str = None) -> List[str]:
        """
        获取所有股票代码列表。
        :param status: 上市状态，None=全部(默认)，L=上市，0=退市
        :return: 股票代码列表，格式如 ['sh.600519', 'sz.000001', ...]
        """
        stocks = query_stock_basic(status=status)
        return [s.code for s in stocks]
    
    def get_symbol_basic_infomation(self, code: str) -> Optional[StockBasic]:
        """
        根据股票代码获取股票基础信息
        :param code: 股票代码
        :return: 股票基础信息数据结构，没查询到则返回None
        """
        stocks = query_stock_basic(code=code)
        if len(stocks) > 0:
            return stocks[0]
        else:
            return None


    # ─────────────────────────────────────────────
    # 价格行情类接口
    # ─────────────────────────────────────────────

    def get_kline(self, symbols: List[str], start_date: str, end_date: str) -> List[DailyKline]:
        """
        获取指定日期范围内的股票行情（按日期升序）。
        :param symbols: 股票代码列表,可以为空，空表示获取所有股票行情
        :param start_date: 起始日期，格式 YYYY-MM-DD
        :param end_date: 结束日期，格式 YYYY-MM-DD
        :return: 收盘价列表，无数据返回空列表
        """
        klines = query_daily_kline(
            codes=symbols,
            start_date=start_date, end_date=end_date,
            order_by="date ASC",
        )
        return klines

    # def get_price_list(symbol: str, days: int) -> list[float]:
    #     """
    #     获取最近 N 个交易日的收盘价列表（从旧到新）。
    #     :param symbol: 股票代码
    #     :param days: 天数
    #     :return: 价格列表
    #     """
    #     return [get_price(symbol, -(days - 1 - i)) for i in range(days)]


    # def get_price_change_pct(symbol: str, date_offset: int = 0) -> float:
    #     """
    #     获取某日的涨跌幅（%）。
    #     :param symbol: 股票代码
    #     :param date_offset: 相对今天的偏移天数
    #     :return: 涨跌幅，如 3.5 表示涨 3.5%
    #     """
    #     random.seed(abs(hash(symbol + f"chg{date_offset}")))
    #     return round(random.uniform(-10, 10), 2)


    # def get_price_change_pct_list(symbol: str, days: int) -> list[float]:
    #     """
    #     获取最近 N 个交易日的涨跌幅列表（从旧到新）。
    #     :param symbol: 股票代码
    #     :param days: 天数
    #     :return: 涨跌幅列表
    #     """
    #     return [get_price_change_pct(symbol, -(days - 1 - i)) for i in range(days)]


    # # ─────────────────────────────────────────────
    # # 估值类接口
    # # ─────────────────────────────────────────────

    # def get_pe(symbol: str) -> Optional[float]:
    #     """
    #     获取市盈率（TTM）。
    #     :return: PE 值，None 表示亏损或无效
    #     """
    #     random.seed(abs(hash(symbol + "pe")))
    #     return round(random.uniform(5, 80), 1)


    # def get_pb(symbol: str) -> float:
    #     """
    #     获取市净率。
    #     :return: PB 值
    #     """
    #     random.seed(abs(hash(symbol + "pb")))
    #     return round(random.uniform(0.5, 10), 2)


    # def get_ps(symbol: str) -> float:
    #     """
    #     获取市销率。
    #     :return: PS 值
    #     """
    #     random.seed(abs(hash(symbol + "ps")))
    #     return round(random.uniform(0.5, 20), 2)


    # def get_market_cap(symbol: str) -> float:
    #     """
    #     获取总市值（亿元）。
    #     :return: 市值
    #     """
    #     random.seed(abs(hash(symbol + "cap")))
    #     return round(random.uniform(10, 5000), 1)


    # # ─────────────────────────────────────────────
    # # 财务类接口
    # # ─────────────────────────────────────────────

    # def get_revenue(symbol: str, year_offset: int = 0) -> float:
    #     """
    #     获取营业收入（亿元）。
    #     :param year_offset: 相对今年的偏移，0=今年，-1=去年，以此类推
    #     :return: 营收
    #     """
    #     random.seed(abs(hash(symbol + f"rev{year_offset}")))
    #     base = random.uniform(1, 500)
    #     growth = random.uniform(0.85, 1.3)
    #     return round(base * (growth ** (-year_offset)), 2)


    # def get_net_profit(symbol: str, year_offset: int = 0) -> float:
    #     """
    #     获取净利润（亿元）。
    #     :param year_offset: 相对今年的偏移，0=今年，-1=去年，以此类推
    #     :return: 净利润
    #     """
    #     random.seed(abs(hash(symbol + f"profit{year_offset}")))
    #     base = random.uniform(0.1, 100)
    #     growth = random.uniform(0.8, 1.4)
    #     return round(base * (growth ** (-year_offset)), 2)


    # def get_revenue_growth_rate(symbol: str, years: int = 1) -> float:
    #     """
    #     获取营收复合增长率（%），过去 N 年。
    #     :param years: 计算复合增长率的年数
    #     :return: 增长率，如 25.3 表示 25.3%
    #     """
    #     current = get_revenue(symbol, 0)
    #     past = get_revenue(symbol, -years)
    #     if past <= 0:
    #         return 0.0
    #     return round(((current / past) ** (1 / years) - 1) * 100, 2)


    # def get_net_profit_growth_rate(symbol: str, years: int = 1) -> float:
    #     """
    #     获取净利润复合增长率（%），过去 N 年。
    #     :param years: 计算复合增长率的年数
    #     :return: 增长率
    #     """
    #     current = get_net_profit(symbol, 0)
    #     past = get_net_profit(symbol, -years)
    #     if past <= 0:
    #         return 0.0
    #     return round(((current / past) ** (1 / years) - 1) * 100, 2)


    # def get_roe(symbol: str) -> float:
    #     """
    #     获取净资产收益率 ROE（%）。
    #     :return: ROE 值
    #     """
    #     random.seed(abs(hash(symbol + "roe")))
    #     return round(random.uniform(2, 35), 2)


    # def get_gross_margin(symbol: str) -> float:
    #     """
    #     获取毛利率（%）。
    #     :return: 毛利率
    #     """
    #     random.seed(abs(hash(symbol + "gm")))
    #     return round(random.uniform(10, 70), 2)


    # def get_debt_ratio(symbol: str) -> float:
    #     """
    #     获取资产负债率（%）。
    #     :return: 资产负债率
    #     """
    #     random.seed(abs(hash(symbol + "debt")))
    #     return round(random.uniform(10, 80), 2)


    # # ─────────────────────────────────────────────
    # # 股息类接口
    # # ─────────────────────────────────────────────

    # def get_dividend_yield(symbol: str) -> float:
    #     """
    #     获取股息率（%）。
    #     :return: 股息率
    #     """
    #     random.seed(abs(hash(symbol + "div")))
    #     return round(random.uniform(0, 8), 2)


    # # ─────────────────────────────────────────────
    # # 成交量类接口
    # # ─────────────────────────────────────────────

    # def get_volume(symbol: str, date_offset: int = 0) -> float:
    #     """
    #     获取成交量（万手）。
    #     :param date_offset: 相对今天的偏移天数
    #     :return: 成交量
    #     """
    #     random.seed(abs(hash(symbol + f"vol{date_offset}")))
    #     return round(random.uniform(100, 50000), 1)


    # def get_volume_list(symbol: str, days: int) -> list[float]:
    #     """
    #     获取最近 N 日成交量列表（从旧到新）。
    #     :param symbol: 股票代码
    #     :param days: 天数
    #     :return: 成交量列表
    #     """
    #     return [get_volume(symbol, -(days - 1 - i)) for i in range(days)]


    # def get_avg_volume(symbol: str, days: int = 20) -> float:
    #     """
    #     获取过去 N 日平均成交量（万手）。
    #     :param days: 天数
    #     :return: 平均成交量
    #     """
    #     vols = get_volume_list(symbol, days)
    #     return round(sum(vols) / len(vols), 1)



# def strategy(api:StockApi) -> bool:
#     """回测交易策略:获取2026年3月份任意一天收盘价高于5元的股票并打印出对应股票的交易代码"""
#     date_symbols_klines = api.get_kline([], "2026-03-01", "2026-03-31")
#     for kline in date_symbols_klines:
#         if kline.close > 5:
#             print(kline.code)
            

# if __name__ == "__main__":
#     api = StockApi()
#     strategy(api)
 