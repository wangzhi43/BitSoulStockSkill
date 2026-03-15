"""
stock_api.py — 股票数据与回测API接口

策略逻辑可调用此模块中的所有函数来获取股票数据。
当前为模拟实现，真实环境中替换为实际数据源即可。
策略逻辑可调用此模块中的所有函数来获取股票数据和技术指标。
本模块是项目对外的唯一接口，其他模块的实现在内部4个独立文件中。

使用示例:
    from stock_api import StockApi
    
    api = StockApi()
    
    # 获取日线行情表
    klines = api.get_daily_kline(['600519.SH'], '2026-01-01', '2026-03-01')
    
    # 获取技术指标
    sma = api.get_sma('600519.SH', '2026-03-01', 20)
    rsi = api.get_rsi('600519.SH', '2026-03-01', 14)
    
    # 获取性能指标
    report = api.calculate_metrics([1000000, 1050000, 1020000], trades, 1000000, 30)
"""

import sys
from typing import Optional, List, Dict

sys.path.insert(0, __file__.rsplit('/', 1)[0])
from realtime_data_featcher import (
    RealtimeStockQuote,
    RealTimeDataFetcher
)
from data_fetcher import (
    query_stock_basic,
    query_daily_kline,
    query_hour_kline,
    query_weekly_kline,
    query_monthly_kline,
    query_daily_basic,
    query_income,
    query_stock_limit,
    query_daily_limit_list,
    query_daily_bomb_list,
)
from define import (
    DailyKline,
    HourKline,
    WeeklyKline,
    MonthlyKline,
    StockBasic,
    DailyBasic,
    Income,
    StockLimit,
    DailyLimitList,
    DailyBombList,
)


from indicators import (
    get_sma,
    get_ema,
    get_rsi,
    get_bollinger_bands,
    get_macd,
    get_atr,
    get_wma,
    get_tema,
    get_mom,
    get_roc,
    get_cci,
    get_obv,
    get_volume,
    get_kdj,
    get_dmi,
    get_trix,
    get_sar,
    get_williams_r,
    get_psycho,
    get_bias,
    get_tr,
    get_natr,
    get_vwap,
    get_ad,
    get_adosc,
    get_mfi,
    get_cmo,
    get_rocp,
    get_rocr,
    get_aroon,
    get_ultosc,
    get_dema,
    get_kama,
    get_midpoint,
    get_midprice,
    get_pvi,
    get_nvi,
    get_ppo,
    get_roc_r,
    get_stoch,
    get_stochf,
    get_stochrsi,
    get_trange,
    get_ma_channel,
    get_donchian,
    get_keltner,
    get_bbands_width,
    get_bbands_pct,
    get_linearreg,
    get_linearreg_angle,
    get_linearreg_intercept,
    get_linearreg_slope,
    get_stddev,
    get_tsf,
    get_var,
    get_correl,
    get_beta,
    get_ht_dcperiod,
    get_ht_dcphase,
    get_ht_phasor,
    get_ht_sine,
    get_ht_trendmode,
    get_typical_price,
    get_median_price,
    get_weighted_close,
    get_avgp,
    get_asi,
    get_vr,
    get_ar,
    get_br,
    get_brar,
    get_dpo,
    get_bbi,
    get_mass,
    get_xue_channel,
    get_consecutive_rise,
    get_consecutive_fall,
    init_indicators_db,
)

from signals import (
    get_morning_star,
    get_qiming_star,
    get_evening_star,
    get_huanghun_star,
    get_three_white_soldiers,
    get_three_black_crows,
    get_dark_cloud_cover,
    get_rounding_bottom,
    get_ascending_triangle,
    get_top_pattern,
    init_signals_db,
)

from metrics import (
    get_max_drawdown,
    get_max_drawdown_pct,
    get_annualized_return,
    get_total_return,
    get_sharpe_ratio,
    get_win_rate,
    get_profit_loss_ratio,
    get_calmar_ratio,
    get_volatility,
    get_trade_stats,
    generate_report,
)

from backtest_tools import (
    Position,
    TradeResult,
    simulate_trade,
    calculate_trade_cost,
    create_position,
    update_position,
    get_position_value,
    get_position_profit,
    calculate_portfolio_value,
    get_portfolio_positions,
    build_equity_curve,
    calculate_daily_returns,
    should_buy,
    should_sell,
    calculate_drawdown,
    buy,
    sell,
)
import data_fetcher

class StockApi:
    """
    股票数据与回测API接口
    
    本类是项目对外提供的唯一接口，封装了以下功能：
    - 股票基础信息查询
    - K线数据获取
    - 技术指标计算（带缓存）
    - 性能指标计算
    - 回测工具函数
    """

    # ============================================================
    # 初始化
    # ============================================================

    def initialSetup(self):
        data_fetcher.init_db()
        data_fetcher.syn_table_datas()
        init_indicators_db()
        init_signals_db()

    # ============================================================
    # 股票基础信息类接口
    # ============================================================

    def get_all_symbols(self) -> List[str]:
        """
        获取所有股票代码列表。
        :return: 股票代码列表，格式如 ['000001.SZ', '600519.SH', ...]
        """
        stocks = query_stock_basic()
        return [s.ts_code for s in stocks]
    
    def get_symbol_basic_infomation(self, ts_code: str) -> Optional[StockBasic]:
        """
        根据股票代码获取股票基础信息
        :param ts_code: 股票代码，如 000001.SZ
        :return: 股票基础信息数据结构，没查询到则返回None
        """
        stocks = query_stock_basic(ts_code=ts_code)
        if len(stocks) > 0:
            return stocks[0]
        else:
            return None


    # ─────────────────────────────────────────────
    # 价格行情类接口
    # ─────────────────────────────────────────────
    def get_realtime_stock_info(self, code:str) -> RealtimeStockQuote:
        """
        获取指定股票代码的股票实时信息

        参数:
            code  股票代码，如000001.SZ
        返回:
            RealtimeStockQuote 实时股票报价信息
        """
        return RealTimeDataFetcher().request_stock_info(code)

    def query_income(
        self,
        ts_codes: List[str] = [],
        report_type: Optional[str] = None,
        end_date: Optional[str] = None,
        start_end_date: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        order_by: str = "end_date ASC",
    ) -> List[Income]:
        """
        根据条件获取利润信息。

        参数:
            ts_codes        按股票代码列表过滤
            report_type     按报告类型精确过滤（如 "1" 表示合并报表）
            end_date        按报告期结束日期精确过滤，格式 "YYYYMMDD"
            start_end_date  按报告期结束日期范围过滤下限（含），格式 "YYYYMMDD"
            limit           返回最大记录数；为 None 表示不限
            offset          分页偏移量，默认 0
            order_by        排序表达式，默认 "end_date ASC"

        返回:
            List[Income]  符合条件的利润表对象列表

        示例:
            # 查询某只股票全部利润表（合并报表）
            records = query_income(ts_codes=["000001.SZ"], report_type="1")

            # 查询某报告期全市场数据
            records = query_income(end_date="20231231")

            # 查询最新一期
            records = query_income(ts_codes=["000001.SZ"], order_by="end_date DESC", limit=1)
        """
        return query_income(
            ts_codes=ts_codes,
            report_type=report_type,
            end_date=end_date,
            start_end_date=start_end_date,
            limit=limit,
            offset=offset,
            order_by=order_by,
        )

    def get_daily_basic(
        self,
        ts_codes: List[str] = [],
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        order_by: str = "trade_date ASC",
    ) -> List[DailyBasic]:
        """
        查询每日基本面指标列表

        参数:
            ts_codes    按股票代码列表过滤
            trade_date  按具体交易日期精确过滤，格式 "YYYY-MM-DD"
            start_date  按日期范围过滤下限（含），格式 "YYYY-MM-DD"
            end_date    按日期范围过滤上限（含），格式 "YYYY-MM-DD"
            limit       返回最大记录数；为 None 表示不限
            offset      分页偏移量，默认 0
            order_by    排序表达式，默认 "trade_date ASC"

        返回:
            List[DailyBasic]  符合条件的每日基本面指标对象列表

        示例:
            # 查询某只股票全部历史基本面数据
            basics = query_daily_basic(ts_codes=["000001.SZ"])

            # 查询某天全市场基本面数据
            basics = query_daily_basic(trade_date="2024-06-03")
        """
        return query_daily_basic(
            ts_codes=ts_codes,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
            order_by=order_by,
        )

    def get_stock_limit(
        self,
        ts_codes: List[str] = [],
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        order_by: str = "trade_date ASC",
    ) -> List[StockLimit]:
        """
        查询每日涨跌停价格列表

        参数:
            ts_codes    按股票代码列表过滤
            trade_date  按具体交易日期精确过滤，格式 "YYYY-MM-DD"
            start_date  按日期范围过滤下限（含），格式 "YYYY-MM-DD"
            end_date    按日期范围过滤上限（含），格式 "YYYY-MM-DD"
            limit       返回最大记录数；为 None 表示不限
            offset      分页偏移量，默认 0
            order_by    排序表达式，默认 "trade_date ASC"

        返回:
            List[StockLimit]  符合条件的每日涨跌停价格对象列表

        示例:
            # 查询某只股票的涨跌停价格历史
            limits = api.get_stock_limit(ts_codes=["000001.SZ"])

            # 查询某天全市场涨跌停价格
            limits = api.get_stock_limit(trade_date="2024-06-03")
        """
        return query_stock_limit(
            ts_codes=ts_codes,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
            order_by=order_by,
        )

    def get_daily_limit_list(
        self,
        ts_codes: List[str] = [],
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit_type: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        order_by: str = "trade_date ASC",
    ) -> List[DailyLimitList]:
        """
        查询每日涨跌停榜单列表

        参数:
            ts_codes    按股票代码列表过滤
            trade_date  按具体交易日期精确过滤，格式 "YYYY-MM-DD"
            start_date  按日期范围过滤下限（含），格式 "YYYY-MM-DD"
            end_date    按日期范围过滤上限（含），格式 "YYYY-MM-DD"
            limit_type  按榜单类型过滤（U=涨停, D=跌停）
            limit       返回最大记录数；为 None 表示不限
            offset      分页偏移量，默认 0
            order_by    排序表达式，默认 "trade_date ASC"

        返回:
            List[DailyLimitList]  符合条件的每日涨跌停榜单对象列表

        示例:
            # 查询某天所有涨停股
            records = api.get_daily_limit_list(trade_date="2024-06-03", limit_type="U")

            # 查询某只股票历史上榜记录
            records = api.get_daily_limit_list(ts_codes=["000001.SZ"])
        """
        return query_daily_limit_list(
            ts_codes=ts_codes,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date,
            limit_type=limit_type,
            limit=limit,
            offset=offset,
            order_by=order_by,
        )

    def get_daily_bomb_list(
        self,
        ts_codes: List[str] = [],
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        bomb_type: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        order_by: str = "trade_date ASC",
    ) -> List[DailyBombList]:
        """
        查询每日炸板榜单列表

        参数:
            ts_codes    按股票代码列表过滤
            trade_date  按具体交易日期精确过滤，格式 "YYYY-MM-DD"
            start_date  按日期范围过滤下限（含），格式 "YYYY-MM-DD"
            end_date    按日期范围过滤上限（含），格式 "YYYY-MM-DD"
            bomb_type   按炸板类型过滤（U=曾涨停, D=曾跌停/撬板）
            limit       返回最大记录数；为 None 表示不限
            offset      分页偏移量，默认 0
            order_by    排序表达式，默认 "trade_date ASC"

        返回:
            List[DailyBombList]  符合条件的每日炸板榜单对象列表

        示例:
            # 查询某天所有炸板（曾涨停）股票
            records = api.get_daily_bomb_list(trade_date="2024-06-03", bomb_type="U")

            # 查询某只股票历史炸板记录
            records = api.get_daily_bomb_list(ts_codes=["000001.SZ"])
        """
        return query_daily_bomb_list(
            ts_codes=ts_codes,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date,
            bomb_type=bomb_type,
            limit=limit,
            offset=offset,
            order_by=order_by,
        )

    def get_daily_kline(self, symbols: List[str], start_date: str, end_date: str) -> List[DailyKline]:
        """
        获取指定日期范围内的股票日线行情（按日期升序）。
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
  
    def get_hour_kline(self, symbols: List[str], start_date: str, end_date: str) -> List[HourKline]:
        """
        获取指定日期范围内的股票小时线行情（按日期和时间升序）。
        :param symbols: 股票代码列表，可以为空，空表示获取所有股票行情
        :param start_date: 起始日期，格式 YYYY-MM-DD
        :param end_date: 结束日期，格式 YYYY-MM-DD
        :return: HourKline 列表，无数据返回空列表
        """
        return query_hour_kline(
            codes=symbols,
            start_date=start_date, end_date=end_date,
            order_by="date ASC, time ASC",
        )

    def get_weekly_kline(self, symbols: List[str], start_date: str, end_date: str) -> List[WeeklyKline]:
        """
        获取指定日期范围内的股票周线行情（按日期升序）。
        :param symbols: 股票代码列表，可以为空，空表示获取所有股票行情
        :param start_date: 起始日期，格式 YYYY-MM-DD
        :param end_date: 结束日期，格式 YYYY-MM-DD
        :return: WeeklyKline 列表，无数据返回空列表
        """
        return query_weekly_kline(
            codes=symbols,
            start_date=start_date, end_date=end_date,
            order_by="date ASC",
        )

    def get_monthly_kline(self, symbols: List[str], start_date: str, end_date: str) -> List[MonthlyKline]:
        """
        获取指定日期范围内的股票月线行情（按日期升序）。
        :param symbols: 股票代码列表，可以为空，空表示获取所有股票行情
        :param start_date: 起始日期，格式 YYYY-MM-DD
        :param end_date: 结束日期，格式 YYYY-MM-DD
        :return: MonthlyKline 列表，无数据返回空列表
        """
        return query_monthly_kline(
            codes=symbols,
            start_date=start_date, end_date=end_date,
            order_by="date ASC",
        )

    def get_daily_close_prices(self, code: str, start_date: str, end_date: str) -> List[float]:
        """
        获取指定股票的日线收盘价列表（按日期升序）。
        
        Args:
            code: 股票代码
            start_date: 起始日期
            end_date: 结束日期
        
        Returns:
            收盘价列表
        
        Example:
            prices = api.get_daily_close_prices('600519.SH', '2026-01-01', '2026-03-01')
        """
        klines = self.get_daily_kline(code, start_date, end_date)
        return [k.close for k in klines]

    def get_daily_open_prices(self, code: str, start_date: str, end_date: str) -> List[float]:
        """
        获取指定股票的日线开盘价列表。
        Args:
            code: 股票代码
            start_date: 起始日期
            end_date: 结束日期
        
        Returns:
            日线开盘价列表
        """
        klines = self.get_daily_kline(code, start_date, end_date)
        return [k.open for k in klines]

    def get_daily_high_prices(self, code: str, start_date: str, end_date: str) -> List[float]:
        """
        获取指定股票的日线最高价列表。
        
        Args:
            code: 股票代码
            start_date: 起始日期
            end_date: 结束日期
        
        Returns:
            日线最高价列表
        """
        klines = self.get_daily_kline(code, start_date, end_date)
        return [k.high for k in klines]

    def get_daily_low_prices(self, code: str, start_date: str, end_date: str) -> List[float]:
        """
        获取指定股票的日线最低价列表。
        
        Args:
            code: 股票代码
            start_date: 起始日期
            end_date: 结束日期
        
        Returns:
            最低价列表
        """
        klines = self.get_daily_kline(code, start_date, end_date)
        return [k.low for k in klines]

    def get_daily_volumes(self, code: str, start_date: str, end_date: str) -> List[float]:
        """
        获取指定股票的日线成交量列表。
        
        Args:
            code: 股票代码
            start_date: 起始日期
            end_date: 结束日期
        
        Returns:
            日线成交量列表
        """
        klines = self.get_daily_kline(code, start_date, end_date)
        return [k.volume for k in klines]

    def get_daily_pct_chg(self, code: str, start_date: str, end_date: str) -> List[float]:
        """
        获取指定股票的日线涨跌幅列表。
        
        Args:
            code: 股票代码
            start_date: 起始日期
            end_date: 结束日期
        
        Returns:
            日线涨跌幅列表(%)
        """
        klines = self.get_daily_kline(code, start_date, end_date)
        return [k.pctChg for k in klines]

    # ============================================================
    # 技术指标类接口（带缓存）
    # ============================================================

    def get_sma(self, code: str, date: str, period: int = 20, use_adjusted: bool = True) -> Optional[float]:
        """
        获取简单移动平均SMA。
        
        Args:
            code: 股票代码
            date: 计算日期，格式 YYYY-MM-DD
            period: 周期，默认20
        
        Returns:
            SMA值，若数据不足返回None
        
        Example:
            sma = api.get_sma('600519.SH', '2026-03-01', 20)
        """
        return get_sma(code, date, period, use_adjusted)

    def get_ema(self, code: str, date: str, period: int = 12, use_adjusted: bool = True) -> Optional[float]:
        """
        获取指数移动平均EMA。
        
        Args:
            code: 股票代码
            date: 计算日期
            period: 周期，默认12
        
        Returns:
            EMA值，若数据不足返回None
        """
        return get_ema(code, date, period, use_adjusted)

    def get_rsi(self, code: str, date: str, period: int = 14, use_adjusted: bool = True) -> Optional[float]:
        """
        获取相对强弱指标RSI。
        
        Args:
            code: 股票代码
            date: 计算日期
            period: 周期，默认14
        
        Returns:
            RSI值(0-100)，若数据不足返回None
        
        Example:
            rsi = api.get_rsi('600519.SH', '2026-03-01', 14)
            if rsi and rsi < 30:
                print('超卖')
        """
        return get_rsi(code, date, period, use_adjusted)

    def get_bollinger_bands(self, code: str, date: str, period: int = 20, std_dev: int = 2, use_adjusted: bool = True) -> Optional[Dict[str, float]]:
        """
        获取布林带指标。
        
        Args:
            code: 股票代码
            date: 计算日期
            period: 周期，默认20
            std_dev: 标准差倍数，默认2
        
        Returns:
            字典 {'upper': 上轨, 'middle': 中轨, 'lower': 下轨}，若数据不足返回None
        
        Example:
            bb = api.get_bollinger_bands('600519.SH', '2026-03-01')
            if bb and close > bb['upper']:
                print('突破上轨')
        """
        return get_bollinger_bands(code, date, period, std_dev, use_adjusted)

    def get_macd(self, code: str, date: str, fast: int = 12, slow: int = 26, signal: int = 9, use_adjusted: bool = True) -> Optional[Dict[str, float]]:
        """
        获取MACD指标。
        
        Args:
            code: 股票代码
            date: 计算日期
            fast: 快线周期，默认12
            slow: 慢线周期，默认26
            signal: 信号线周期，默认9
        
        Returns:
            字典 {'macd': MACD线, 'signal': 信号线, 'histogram': 柱状图}，若数据不足返回None
        
        Example:
            macd = api.get_macd('600519.SH', '2026-03-01')
            if macd and macd['histogram'] > 0:
                print('多头')
        """
        return get_macd(code, date, fast, slow, signal, use_adjusted)

    def get_atr(self, code: str, date: str, period: int = 14, use_adjusted: bool = True) -> Optional[float]:
        """
        获取平均真实波幅ATR。
        
        Args:
            code: 股票代码
            date: 计算日期
            period: 周期，默认14
        
        Returns:
            ATR值，若数据不足返回None
        """
        return get_atr(code, date, period, use_adjusted)

    def get_wma(self, code: str, date: str, period: int = 20, use_adjusted: bool = True) -> Optional[float]:
        """
        获取加权移动平均WMA。
        
        Args:
            code: 股票代码
            date: 计算日期
            period: 周期，默认20
        
        Returns:
            WMA值，若数据不足返回None
        """
        return get_wma(code, date, period, use_adjusted)

    def get_tema(self, code: str, date: str, period: int = 20, use_adjusted: bool = True) -> Optional[float]:
        """
        获取三重指数移动平均TEMA。
        
        Args:
            code: 股票代码
            date: 计算日期
            period: 周期，默认20
        
        Returns:
            TEMA值，若数据不足返回None
        """
        return get_tema(code, date, period, use_adjusted)

    def get_mom(self, code: str, date: str, period: int = 10, use_adjusted: bool = True) -> Optional[float]:
        """
        获取动量指标MOM。
        
        Args:
            code: 股票代码
            date: 计算日期
            period: 周期，默认10
        
        Returns:
            MOM值，若数据不足返回None
        """
        return get_mom(code, date, period, use_adjusted)

    def get_roc(self, code: str, date: str, period: int = 10, use_adjusted: bool = True) -> Optional[float]:
        """
        获取变动率指标ROC(%)。
        
        Args:
            code: 股票代码
            date: 计算日期
            period: 周期，默认10
        
        Returns:
            ROC值(%)，若数据不足返回None
        """
        return get_roc(code, date, period, use_adjusted)

    def get_cci(self, code: str, date: str, period: int = 20, use_adjusted: bool = True) -> Optional[float]:
        """
        获取顺势指标CCI。
        
        Args:
            code: 股票代码
            date: 计算日期
            period: 周期，默认20
        
        Returns:
            CCI值，若数据不足返回None
        """
        return get_cci(code, date, period, use_adjusted)

    def get_obv(self, code: str, date: str, period: int = 20, use_adjusted: bool = True) -> Optional[float]:
        """
        获取能量潮OBV。
        
        Args:
            code: 股票代码
            date: 计算日期
            period: 周期，默认20
        
        Returns:
            OBV值，若数据不足返回None
        """
        return get_obv(code, date, period, use_adjusted)

    def get_volume(self, code: str, date: str, period: int = 20, use_adjusted: bool = True) -> Optional[Dict[str, float]]:
        """
        获取成交量指标。
        
        Args:
            code: 股票代码
            date: 计算日期
            period: 周期，默认20
        
        Returns:
            字典 {'current': 当前成交量, 'sma': 成交量均线}，若数据不足返回None
        """
        return get_volume(code, date, period, use_adjusted)

    def get_kdj(self, code: str, date: str, n: int = 9, m1: int = 3, m2: int = 3, use_adjusted: bool = True) -> Optional[Dict[str, float]]:
        """
        获取随机指标KDJ。
        
        Args:
            code: 股票代码
            date: 计算日期
            n: 周期，默认9
            m1: 平滑参数1，默认3
            m2: 平滑参数2，默认3
        
        Returns:
            字典 {'k': K值, 'd': D值, 'j': J值}，若数据不足返回None
        """
        return get_kdj(code, date, n, m1, m2, use_adjusted)

    def get_dmi(self, code: str, date: str, period: int = 14, use_adjusted: bool = True) -> Optional[Dict[str, float]]:
        """
        获取趋向指标DMI。
        
        Args:
            code: 股票代码
            date: 计算日期
            period: 周期，默认14
        
        Returns:
            字典 {'pdi': +DI, 'mdi': -DI, 'adx': ADX}，若数据不足返回None
        """
        return get_dmi(code, date, period, use_adjusted)

    def get_trix(self, code: str, date: str, period: int = 12, use_adjusted: bool = True) -> Optional[float]:
        """
        获取三重指数平滑移动平均TRIX(%)。
        
        Args:
            code: 股票代码
            date: 计算日期
            period: 周期，默认12
        
        Returns:
            TRIX值(%)，若数据不足返回None
        """
        return get_trix(code, date, period, use_adjusted)

    def get_sar(self, code: str, date: str, af_start: float = 0.02, af_max: float = 0.2, use_adjusted: bool = True) -> Optional[Dict[str, float]]:
        """
        获取抛物线转向SAR。
        
        Args:
            code: 股票代码
            date: 计算日期
            af_start: 加速因子起始值，默认0.02
            af_max: 加速因子最大值，默认0.2
        
        Returns:
            字典 {'sar': SAR值, 'trend': 趋势}，若数据不足返回None
        """
        return get_sar(code, date, af_start, af_max, use_adjusted)

    def get_williams_r(self, code: str, date: str, period: int = 14, use_adjusted: bool = True) -> Optional[float]:
        """
        获取威廉指标WR(0-100)。
        
        Args:
            code: 股票代码
            date: 计算日期
            period: 周期，默认14
        
        Returns:
            WR值(0-100)，0表示超买，100表示超卖，若数据不足返回None
        """
        return get_williams_r(code, date, period, use_adjusted)

    def get_psycho(self, code: str, date: str, period: int = 12, use_adjusted: bool = True) -> Optional[float]:
        """
        获取心理线PSY(0-100)。
        
        Args:
            code: 股票代码
            date: 计算日期
            period: 周期，默认12
        
        Returns:
            PSY值(0-100)，若数据不足返回None
        """
        return get_psycho(code, date, period, use_adjusted)

    def get_bias(self, code: str, date: str, period: int = 20, use_adjusted: bool = True) -> Optional[float]:
        """
        获取乖离率BIAS(%)。
        
        Args:
            code: 股票代码
            date: 计算日期
            period: 周期，默认20
        
        Returns:
            BIAS值(%)，若数据不足返回None
        """
        return get_bias(code, date, period, use_adjusted)

    def get_tr(self, code: str, date: str, use_adjusted: bool = True) -> Optional[float]:
        """
        获取真实波幅TR。
        
        Args:
            code: 股票代码
            date: 计算日期
        
        Returns:
            TR值，若数据不足返回None
        """
        return get_tr(code, date, use_adjusted)

    def get_natr(self, code: str, date: str, period: int = 14, use_adjusted: bool = True) -> Optional[float]:
        """
        获取归一化平均真实波幅NATR(%)。
        
        Args:
            code: 股票代码
            date: 计算日期
            period: 周期，默认14
        
        Returns:
            NATR值(%)，若数据不足返回None
        """
        return get_natr(code, date, period, use_adjusted)

    def get_vwap(self, code: str, date: str, period: int = 20, use_adjusted: bool = True) -> Optional[float]:
        """
        获取成交量加权平均价VWAP。
        
        Args:
            code: 股票代码
            date: 计算日期
            period: 周期，默认20
        
        Returns:
            VWAP值，若数据不足返回None
        """
        return get_vwap(code, date, period, use_adjusted)

    def get_ad(self, code: str, date: str, period: int = 20, use_adjusted: bool = True) -> Optional[float]:
        """
        获取累积/派发线AD。
        
        Args:
            code: 股票代码
            date: 计算日期
            period: 周期，默认20
        
        Returns:
            AD值，若数据不足返回None
        """
        return get_ad(code, date, period, use_adjusted)

    def get_adosc(self, code: str, date: str, fast: int = 3, slow: int = 10, use_adjusted: bool = True) -> Optional[float]:
        """
        获取震荡指标ADOSC。
        
        Args:
            code: 股票代码
            date: 计算日期
            fast: 快线周期，默认3
            slow: 慢线周期，默认10
        
        Returns:
            ADOSC值，若数据不足返回None
        """
        return get_adosc(code, date, fast, slow, use_adjusted)

    def get_mfi(self, code: str, date: str, period: int = 14, use_adjusted: bool = True) -> Optional[float]:
        """
        获取资金流量指标MFI(0-100)。
        
        Args:
            code: 股票代码
            date: 计算日期
            period: 周期，默认14
        
        Returns:
            MFI值(0-100)，若数据不足返回None
        """
        return get_mfi(code, date, period, use_adjusted)

    def get_cmo(self, code: str, date: str, period: int = 14, use_adjusted: bool = True) -> Optional[float]:
        """
        获取钱德动量摆动指标CMO(-100 to 100)。
        
        Args:
            code: 股票代码
            date: 计算日期
            period: 周期，默认14
        
        Returns:
            CMO值(-100 to 100)，若数据不足返回None
        """
        return get_cmo(code, date, period, use_adjusted)

    def get_rocp(self, code: str, date: str, period: int = 10, use_adjusted: bool = True) -> Optional[float]:
        """
        获取价格变动率ROCP。
        
        Args:
            code: 股票代码
            date: 计算日期
            period: 周期，默认10
        
        Returns:
            ROCP值，若数据不足返回None
        """
        return get_rocp(code, date, period, use_adjusted)

    def get_rocr(self, code: str, date: str, period: int = 10, use_adjusted: bool = True) -> Optional[float]:
        """
        获取价格变动率比ROCR。
        
        Args:
            code: 股票代码
            date: 计算日期
            period: 周期，默认10
        
        Returns:
            ROCR值，若数据不足返回None
        """
        return get_rocr(code, date, period, use_adjusted)

    def get_aroon(self, code: str, date: str, period: int = 14, use_adjusted: bool = True) -> Optional[Dict[str, float]]:
        """
        获取阿隆指标AROON。
        
        Args:
            code: 股票代码
            date: 计算日期
            period: 周期，默认14
        
        Returns:
            字典 {'up': AROON_UP, 'down': AROON_DOWN, 'osc': AROON_OSC}，若数据不足返回None
        """
        return get_aroon(code, date, period, use_adjusted)

    def get_ultosc(self, code: str, date: str, period1: int = 7, period2: int = 14, period3: int = 28, use_adjusted: bool = True) -> Optional[float]:
        """
        获取终极振荡器ULTOSC(0-100)。
        
        Args:
            code: 股票代码
            date: 计算日期
            period1: 周期1，默认7
            period2: 周期2，默认14
            period3: 周期3，默认28
        
        Returns:
            ULTOSC值(0-100)，若数据不足返回None
        """
        return get_ultosc(code, date, period1, period2, period3, use_adjusted)

    def get_dema(self, code: str, date: str, period: int = 20, use_adjusted: bool = True) -> Optional[float]:
        """
        获取双重指数移动平均DEMA。
        
        Args:
            code: 股票代码
            date: 计算日期
            period: 周期，默认20
        
        Returns:
            DEMA值，若数据不足返回None
        """
        return get_dema(code, date, period, use_adjusted)

    def get_kama(self, code: str, date: str, period: int = 10, use_adjusted: bool = True) -> Optional[float]:
        """
        获取考夫曼自适应移动平均KAMA。
        
        Args:
            code: 股票代码
            date: 计算日期
            period: 周期，默认10
        
        Returns:
            KAMA值，若数据不足返回None
        """
        return get_kama(code, date, period, use_adjusted)

    def get_midpoint(self, code: str, date: str, period: int = 14, use_adjusted: bool = True) -> Optional[float]:
        """
        获取中点价格MIDPOINT。
        
        Args:
            code: 股票代码
            date: 计算日期
            period: 周期，默认14
        
        Returns:
            MIDPOINT值，若数据不足返回None
        """
        return get_midpoint(code, date, period, use_adjusted)

    def get_midprice(self, code: str, date: str, period: int = 14, use_adjusted: bool = True) -> Optional[float]:
        """
        获取中点价格MIDPRICE。
        
        Args:
            code: 股票代码
            date: 计算日期
            period: 周期，默认14
        
        Returns:
            MIDPRICE值，若数据不足返回None
        """
        return get_midprice(code, date, period, use_adjusted)

    def get_pvi(self, code: str, date: str, period: int = 20, use_adjusted: bool = True) -> Optional[float]:
        """
        获取正成交量指标PVI。
        
        Args:
            code: 股票代码
            date: 计算日期
            period: 周期，默认20
        
        Returns:
            PVI值，若数据不足返回None
        """
        return get_pvi(code, date, period, use_adjusted)

    def get_nvi(self, code: str, date: str, period: int = 20, use_adjusted: bool = True) -> Optional[float]:
        """
        获取负成交量指标NVI。
        
        Args:
            code: 股票代码
            date: 计算日期
            period: 周期，默认20
        
        Returns:
            NVI值，若数据不足返回None
        """
        return get_nvi(code, date, period, use_adjusted)

    def get_ppo(self, code: str, date: str, fast: int = 12, slow: int = 26, signal: int = 9, use_adjusted: bool = True) -> Optional[Dict[str, float]]:
        """
        获取价格震荡指标PPO。
        
        Args:
            code: 股票代码
            date: 计算日期
            fast: 快线周期，默认12
            slow: 慢线周期，默认26
            signal: 信号线周期，默认9
        
        Returns:
            字典 {'ppo': PPO线, 'signal': 信号线, 'histogram': 柱状图}，若数据不足返回None
        """
        return get_ppo(code, date, fast, slow, signal, use_adjusted)

    def get_roc_r(self, code: str, date: str, period: int = 10, use_adjusted: bool = True) -> Optional[float]:
        """
        获取变动率ROC_R。
        
        Args:
            code: 股票代码
            date: 计算日期
            period: 周期，默认10
        
        Returns:
            ROC_R值，若数据不足返回None
        """
        return get_roc_r(code, date, period, use_adjusted)

    def get_stoch(self, code: str, date: str, fastk_period: int = 14, slowk_period: int = 3, slowd_period: int = 3, use_adjusted: bool = True) -> Optional[Dict[str, float]]:
        """
        获取随机指标STOCH。
        
        Args:
            code: 股票代码
            date: 计算日期
            fastk_period: 快速K周期，默认14
            slowk_period: 慢速K周期，默认3
            slowd_period: 慢速D周期，默认3
        
        Returns:
            字典 {'slowk': 慢速K, 'slowd': 慢速D}，若数据不足返回None
        """
        return get_stoch(code, date, fastk_period, slowk_period, slowd_period, use_adjusted)

    def get_stochf(self, code: str, date: str, fastk_period: int = 14, fastd_period: int = 3, use_adjusted: bool = True) -> Optional[Dict[str, float]]:
        """
        获取快速随机指标STOCHF。
        
        Args:
            code: 股票代码
            date: 计算日期
            fastk_period: 快速K周期，默认14
            fastd_period: 快速D周期，默认3
        
        Returns:
            字典 {'fastk': 快速K, 'fastd': 快速D}，若数据不足返回None
        """
        return get_stochf(code, date, fastk_period, fastd_period, use_adjusted)

    def get_stochrsi(self, code: str, date: str, rsi_period: int = 14, stoch_period: int = 14, use_adjusted: bool = True) -> Optional[Dict[str, float]]:
        """
        获取随机RSI指标STOCHRSI。
        
        Args:
            code: 股票代码
            date: 计算日期
            rsi_period: RSI周期，默认14
            stoch_period: 随机周期，默认14
        
        Returns:
            字典 {'fastk': K, 'fastd': D}，若数据不足返回None
        """
        return get_stochrsi(code, date, rsi_period, stoch_period, use_adjusted)

    def get_trange(self, code: str, date: str, use_adjusted: bool = True) -> Optional[float]:
        """
        获取真实波幅TRANGE。
        
        Args:
            code: 股票代码
            date: 计算日期
        
        Returns:
            TRANGE值，若数据不足返回None
        """
        return get_trange(code, date, use_adjusted)

    def get_ma_channel(self, code: str, date: str, period: int = 20, multiplier: float = 2.0, use_adjusted: bool = True) -> Optional[Dict[str, float]]:
        """
        获取移动平均通道。
        
        Args:
            code: 股票代码
            date: 计算日期
            period: 周期，默认20
            multiplier: 倍数，默认2.0
        
        Returns:
            字典 {'upper': 上轨, 'middle': 中轨, 'lower': 下轨}，若数据不足返回None
        """
        return get_ma_channel(code, date, period, multiplier, use_adjusted)

    def get_donchian(self, code: str, date: str, period: int = 20, use_adjusted: bool = True) -> Optional[Dict[str, float]]:
        """
        获取唐奇安通道。
        
        Args:
            code: 股票代码
            date: 计算日期
            period: 周期，默认20
        
        Returns:
            字典 {'upper': 上轨, 'middle': 中轨, 'lower': 下轨}，若数据不足返回None
        """
        return get_donchian(code, date, period, use_adjusted)

    def get_keltner(self, code: str, date: str, ma_period: int = 20, atr_period: int = 10, multiplier: float = 2.0, use_adjusted: bool = True) -> Optional[Dict[str, float]]:
        """
        获取凯尔特纳通道。
        
        Args:
            code: 股票代码
            date: 计算日期
            ma_period: MA周期，默认20
            atr_period: ATR周期，默认10
            multiplier: 倍数，默认2.0
        
        Returns:
            字典 {'upper': 上轨, 'middle': 中轨, 'lower': 下轨}，若数据不足返回None
        """
        return get_keltner(code, date, ma_period, atr_period, multiplier, use_adjusted)

    def get_bbands_width(self, code: str, date: str, period: int = 20, std_dev: int = 2, use_adjusted: bool = True) -> Optional[float]:
        """
        获取布林带宽度BBANDS_WIDTH(%)。
        
        Args:
            code: 股票代码
            date: 计算日期
            period: 周期，默认20
            std_dev: 标准差倍数，默认2
        
        Returns:
            BBANDS_WIDTH值(%)，若数据不足返回None
        """
        return get_bbands_width(code, date, period, std_dev, use_adjusted)

    def get_bbands_pct(self, code: str, date: str, period: int = 20, std_dev: int = 2, use_adjusted: bool = True) -> Optional[float]:
        """
        获取布林带百分比位置BBANDS_PCT(0-1)。
        
        Args:
            code: 股票代码
            date: 计算日期
            period: 周期，默认20
            std_dev: 标准差倍数，默认2
        
        Returns:
            BBANDS_PCT值(0-1)，若数据不足返回None
        """
        return get_bbands_pct(code, date, period, std_dev, use_adjusted)

    def get_linearreg(self, code: str, date: str, period: int = 14, use_adjusted: bool = True) -> Optional[float]:
        """
        获取线性回归预测值LINEARREG。
        
        Args:
            code: 股票代码
            date: 计算日期
            period: 周期，默认14
        
        Returns:
            LINEARREG值，若数据不足返回None
        """
        return get_linearreg(code, date, period, use_adjusted)

    def get_linearreg_angle(self, code: str, date: str, period: int = 14, use_adjusted: bool = True) -> Optional[float]:
        """
        获取线性回归角度LINEARREG_ANGLE。
        
        Args:
            code: 股票代码
            date: 计算日期
            period: 周期，默认14
        
        Returns:
            LINEARREG_ANGLE值，若数据不足返回None
        """
        return get_linearreg_angle(code, date, period, use_adjusted)

    def get_linearreg_intercept(self, code: str, date: str, period: int = 14, use_adjusted: bool = True) -> Optional[float]:
        """
        获取线性回归截距LINEARREG_INTERCEPT。
        
        Args:
            code: 股票代码
            date: 计算日期
            period: 周期，默认14
        
        Returns:
            LINEARREG_INTERCEPT值，若数据不足返回None
        """
        return get_linearreg_intercept(code, date, period, use_adjusted)

    def get_linearreg_slope(self, code: str, date: str, period: int = 14, use_adjusted: bool = True) -> Optional[float]:
        """
        获取线性回归斜率LINEARREG_SLOPE。
        
        Args:
            code: 股票代码
            date: 计算日期
            period: 周期，默认14
        
        Returns:
            LINEARREG_SLOPE值，若数据不足返回None
        """
        return get_linearreg_slope(code, date, period, use_adjusted)

    def get_stddev(self, code: str, date: str, period: int = 20, nbdev: int = 1, use_adjusted: bool = True) -> Optional[float]:
        """
        获取标准差STDDEV。
        
        Args:
            code: 股票代码
            date: 计算日期
            period: 周期，默认20
            nbdev: 标准差倍数，默认1
        
        Returns:
            STDDEV值，若数据不足返回None
        """
        return get_stddev(code, date, period, nbdev, use_adjusted)

    def get_tsf(self, code: str, date: str, period: int = 14, use_adjusted: bool = True) -> Optional[float]:
        """
        获取时间序列预测TSF。
        
        Args:
            code: 股票代码
            date: 计算日期
            period: 周期，默认14
        
        Returns:
            TSF值，若数据不足返回None
        """
        return get_tsf(code, date, period, use_adjusted)

    def get_var(self, code: str, date: str, period: int = 20, nbdev: int = 1, use_adjusted: bool = True) -> Optional[float]:
        """
        获取方差VAR。
        
        Args:
            code: 股票代码
            date: 计算日期
            period: 周期，默认20
            nbdev: 倍数，默认1
        
        Returns:
            VAR值，若数据不足返回None
        """
        return get_var(code, date, period, nbdev, use_adjusted)

    def get_correl(self, code: str, date: str, period: int = 20, use_adjusted: bool = True) -> Optional[float]:
        """
        获取相关系数CORREL(固定返回1.0)。
        
        Args:
            code: 股票代码
            date: 计算日期
            period: 周期，默认20
        
        Returns:
            CORREL值(固定1.0)
        """
        return get_correl(code, date, period, use_adjusted)

    def get_beta(self, code: str, date: str, period: int = 20, use_adjusted: bool = True) -> Optional[float]:
        """
        获取贝塔系数BETA(固定返回1.0)。
        
        Args:
            code: 股票代码
            date: 计算日期
            period: 周期，默认20
        
        Returns:
            BETA值(固定1.0)
        """
        return get_beta(code, date, period, use_adjusted)

    def get_ht_dcperiod(self, code: str, date: str, use_adjusted: bool = True) -> Optional[float]:
        """
        获取希尔伯特变换-主导周期HT_DCPERIOD。
        
        Args:
            code: 股票代码
            date: 计算日期
        
        Returns:
            HT_DCPERIOD值，若数据不足返回None
        """
        return get_ht_dcperiod(code, date, use_adjusted)

    def get_ht_dcphase(self, code: str, date: str, use_adjusted: bool = True) -> Optional[float]:
        """
        获取希尔伯特变换-主导相位HT_DCPHASE。
        
        Args:
            code: 股票代码
            date: 计算日期
        
        Returns:
            HT_DCPHASE值，若数据不足返回None
        """
        return get_ht_dcphase(code, date, use_adjusted)

    def get_ht_phasor(self, code: str, date: str, use_adjusted: bool = True) -> Optional[Dict[str, float]]:
        """
        获取希尔伯特变换-相位分量HT_PHASOR。
        
        Args:
            code: 股票代码
            date: 计算日期
        
        Returns:
            字典 {'inphase': 同相, 'quadrature': 正交}，若数据不足返回None
        """
        return get_ht_phasor(code, date, use_adjusted)

    def get_ht_sine(self, code: str, date: str, use_adjusted: bool = True) -> Optional[Dict[str, float]]:
        """
        获取希尔伯特变换-正弦波HT_SINE。
        
        Args:
            code: 股票代码
            date: 计算日期
        
        Returns:
            字典 {'sine': 正弦, 'leadsine': 超前正弦}，若数据不足返回None
        """
        return get_ht_sine(code, date, use_adjusted)

    def get_ht_trendmode(self, code: str, date: str, use_adjusted: bool = True) -> Optional[int]:
        """
        获取希尔伯特变换-趋势模式HT_TRENDMODE。
        
        Args:
            code: 股票代码
            date: 计算日期
        
        Returns:
            1=趋势, 0=周期，若数据不足返回None
        """
        return get_ht_trendmode(code, date, use_adjusted)

    def get_typical_price(self, code: str, date: str, use_adjusted: bool = True) -> Optional[float]:
        """
        获取典型价格TP = (High + Low + Close) / 3。
        
        Args:
            code: 股票代码
            date: 计算日期
        
        Returns:
            典型价格，若数据不足返回None
        """
        return get_typical_price(code, date, use_adjusted)

    def get_median_price(self, code: str, date: str, use_adjusted: bool = True) -> Optional[float]:
        """
        获取中位数价格 = (High + Low) / 2。
        
        Args:
            code: 股票代码
            date: 计算日期
        
        Returns:
            中位数价格，若数据不足返回None
        """
        return get_median_price(code, date, use_adjusted)

    def get_weighted_close(self, code: str, date: str, use_adjusted: bool = True) -> Optional[float]:
        """
        获取加权收盘价 = (High + Low + 2 * Close) / 4。
        
        Args:
            code: 股票代码
            date: 计算日期
        
        Returns:
            加权收盘价，若数据不足返回None
        """
        return get_weighted_close(code, date, use_adjusted)

    def get_avgp(self, code: str, date: str, use_adjusted: bool = True) -> Optional[float]:
        """
        获取平均价格 = (Open + High + Low + Close) / 4。
        
        Args:
            code: 股票代码
            date: 计算日期
        
        Returns:
            平均价格，若数据不足返回None
        """
        return get_avgp(code, date, use_adjusted)

    def get_asi(self, code: str, date: str, period: int = 26, use_adjusted: bool = True) -> Optional[float]:
        """
        获取累积摆动指数 ASI（Accumulative Swing Index）。

        ASI 基于开高低收四价构造，用于衡量价格摆动的累积强度，
        值域无固定范围，正值表示多头动能积累，负值表示空头动能积累。

        Args:
            code: 股票代码
            date: 计算日期，格式 YYYY-MM-DD
            period: 历史K线根数，默认26
            use_adjusted: 是否使用后复权价格，默认True

        Returns:
            ASI值（float），数据不足时返回None

        Example:
            asi = api.get_asi('600519.SH', '2026-03-01', 26)
        """
        return get_asi(code, date, period, use_adjusted)

    def get_vr(self, code: str, date: str, period: int = 26, use_adjusted: bool = True) -> Optional[float]:
        """
        获取成交量比率指标 VR（Volume Ratio）。

        VR = (上涨日成交量之和 + 0.5 * 平盘日成交量) / (下跌日成交量之和 + 0.5 * 平盘日成交量)。
        VR > 1 表示量价配合偏多，VR < 1 表示量价配合偏空，正常区间约 0.5 ~ 1.5。

        Args:
            code: 股票代码
            date: 计算日期，格式 YYYY-MM-DD
            period: 统计周期，默认26
            use_adjusted: 是否使用后复权价格，默认True

        Returns:
            VR值（float），数据不足时返回None

        Example:
            vr = api.get_vr('600519.SH', '2026-03-01', 26)
        """
        return get_vr(code, date, period, use_adjusted)

    def get_ar(self, code: str, date: str, period: int = 26, use_adjusted: bool = True) -> Optional[float]:
        """
        获取人气指标 AR（Atmosphere/Rally）。

        AR = sum(High - Open) / sum(Open - Low) * 100，衡量多空双方相对强弱，
        100 为均衡，> 100 多头占优，< 100 空头占优，一般正常范围 50 ~ 150。

        Args:
            code: 股票代码
            date: 计算日期，格式 YYYY-MM-DD
            period: 统计周期，默认26
            use_adjusted: 是否使用后复权价格，默认True

        Returns:
            AR值（float），数据不足时返回None

        Example:
            ar = api.get_ar('600519.SH', '2026-03-01', 26)
        """
        return get_ar(code, date, period, use_adjusted)

    def get_br(self, code: str, date: str, period: int = 26, use_adjusted: bool = True) -> Optional[float]:
        """
        获取意愿指标 BR（Buyer/Seller Ratio）。

        BR = sum(High - Close_prev) / sum(Close_prev - Low) * 100，衡量多空力量对比，
        与 AR 配合使用：BR > AR 多头强势，BR < AR 空头强势。

        Args:
            code: 股票代码
            date: 计算日期，格式 YYYY-MM-DD
            period: 统计周期，默认26
            use_adjusted: 是否使用后复权价格，默认True

        Returns:
            BR值（float），数据不足时返回None

        Example:
            br = api.get_br('600519.SH', '2026-03-01', 26)
        """
        return get_br(code, date, period, use_adjusted)

    def get_brar(self, code: str, date: str, period: int = 26, use_adjusted: bool = True) -> Optional[Dict[str, float]]:
        """
        同时获取人气指标 AR 和意愿指标 BR。

        BRAR 是 AR 与 BR 的组合指标，二者结合判断市场多空力量：
        - AR 衡量当日多空（基于开盘价）
        - BR 衡量跨日多空（基于前收价）

        Args:
            code: 股票代码
            date: 计算日期，格式 YYYY-MM-DD
            period: 统计周期，默认26
            use_adjusted: 是否使用后复权价格，默认True

        Returns:
            字典 {'ar': float, 'br': float}，数据不足时返回None

        Example:
            brar = api.get_brar('600519.SH', '2026-03-01', 26)
            ar, br = brar['ar'], brar['br']
        """
        return get_brar(code, date, period, use_adjusted)

    def get_dpo(self, code: str, date: str, period: int = 20, use_adjusted: bool = True) -> Optional[float]:
        """
        获取去趋势震荡指标 DPO（Detrended Price Oscillator）。

        DPO = Close - SMA(Close, period)[-(period/2 + 1)]，通过去除长期趋势
        来识别价格的短中期周期性波动，穿越零轴可作为买卖参考信号。

        Args:
            code: 股票代码
            date: 计算日期，格式 YYYY-MM-DD
            period: 周期，默认20
            use_adjusted: 是否使用后复权价格，默认True

        Returns:
            DPO值（float），数据不足时返回None

        Example:
            dpo = api.get_dpo('600519.SH', '2026-03-01', 20)
        """
        return get_dpo(code, date, period, use_adjusted)

    def get_bbi(self, code: str, date: str, use_adjusted: bool = True) -> Optional[float]:
        """
        获取多空指标 BBI（Bull and Bear Index）。

        BBI = (MA3 + MA6 + MA12 + MA24) / 4，是四条均线的算术平均值，
        价格上穿 BBI 为多头信号，下穿为空头信号。固定使用 3/6/12/24 周期。

        Args:
            code: 股票代码
            date: 计算日期，格式 YYYY-MM-DD
            use_adjusted: 是否使用后复权价格，默认True

        Returns:
            BBI值（float），数据不足时返回None

        Example:
            bbi = api.get_bbi('600519.SH', '2026-03-01')
        """
        return get_bbi(code, date, use_adjusted)

    def get_mass(self, code: str, date: str, ema_period: int = 9, period: int = 25, use_adjusted: bool = True) -> Optional[float]:
        """
        获取梅斯线 MASS Index（Mass Index）。

        MASS = sum(EMA(H-L, p) / EMA(EMA(H-L, p), p), period)，通过高低价差
        的双重 EMA 比值累加来识别价格反转，值升破 27 后回落至 26.5 以下为
        "反转鼓"信号。

        Args:
            code: 股票代码
            date: 计算日期，格式 YYYY-MM-DD
            ema_period: EMA平滑周期，默认9
            period: 累积周期，默认25
            use_adjusted: 是否使用后复权价格，默认True

        Returns:
            MASS值（float），数据不足时返回None

        Example:
            mass = api.get_mass('600519.SH', '2026-03-01', 9, 25)
        """
        return get_mass(code, date, ema_period, period, use_adjusted)

    def get_xue_channel(self, code: str, date: str, period: int = 20, use_adjusted: bool = True) -> Optional[Dict[str, float]]:
        """
        获取雪球通道（薛斯通道）。

        雪球通道由中轨（MA）、上轨（MA + k*ATR）、下轨（MA - k*ATR）构成，
        价格突破上轨为超买，跌破下轨为超卖，常用于趋势跟踪和止损设置。

        Args:
            code: 股票代码
            date: 计算日期，格式 YYYY-MM-DD
            period: 均线和ATR周期，默认20
            use_adjusted: 是否使用后复权价格，默认True

        Returns:
            字典 {'upper': float, 'middle': float, 'lower': float}，数据不足时返回None

        Example:
            ch = api.get_xue_channel('600519.SH', '2026-03-01', 20)
            upper, middle, lower = ch['upper'], ch['middle'], ch['lower']
        """
        return get_xue_channel(code, date, period, use_adjusted)

    def get_consecutive_rise(self, code: str, date: str, use_adjusted: bool = True) -> Optional[int]:
        """
        获取截至指定日期连续上涨的天数。

        从指定日期向前追溯，统计收盘价连续高于前一日的天数，
        0 表示当日未上涨，1 表示仅当日上涨，依此类推。

        Args:
            code: 股票代码
            date: 计算日期，格式 YYYY-MM-DD
            use_adjusted: 是否使用后复权价格，默认True

        Returns:
            连续上涨天数（int ≥ 0），数据不足时返回None

        Example:
            n = api.get_consecutive_rise('600519.SH', '2026-03-01')
        """
        return get_consecutive_rise(code, date, use_adjusted)

    def get_consecutive_fall(self, code: str, date: str, use_adjusted: bool = True) -> Optional[int]:
        """
        获取截至指定日期连续下跌的天数。

        从指定日期向前追溯，统计收盘价连续低于前一日的天数，
        0 表示当日未下跌，1 表示仅当日下跌，依此类推。

        Args:
            code: 股票代码
            date: 计算日期，格式 YYYY-MM-DD
            use_adjusted: 是否使用后复权价格，默认True

        Returns:
            连续下跌天数（int ≥ 0），数据不足时返回None

        Example:
            n = api.get_consecutive_fall('600519.SH', '2026-03-01')
        """
        return get_consecutive_fall(code, date, use_adjusted)

    # ============================================================
    # 裸K形态信号类接口（带缓存）
    # ============================================================

    def get_morning_star(self, code: str, date: str, use_adjusted: bool = True) -> Optional[int]:
        """
        检测早晨之星（Morning Star）形态。

        早晨之星是底部反转信号，由三根K线构成：第一根大阴线、第二根十字星
        （开低收于阴线实体下方）、第三根大阳线并收回阴线实体一半以上。

        结果会缓存到 cached_signals 表，相同参数直接读缓存。

        Args:
            code: 股票代码
            date: 判断日期，格式 YYYY-MM-DD（以该日为第三根K线）
            use_adjusted: 是否使用后复权价格，默认True

        Returns:
            1 表示出现形态，0 表示未出现，None 表示数据不足

        Example:
            signal = api.get_morning_star('600519.SH', '2026-03-01')
        """
        return get_morning_star(code, date, use_adjusted)

    def get_qiming_star(self, code: str, date: str, use_adjusted: bool = True) -> Optional[int]:
        """
        检测启明星形态（早晨之星别名）。

        启明星即早晨之星（Morning Star），共享同一缓存键 MORNING_STAR，
        结果与 get_morning_star 完全一致。

        Args:
            code: 股票代码
            date: 判断日期，格式 YYYY-MM-DD
            use_adjusted: 是否使用后复权价格，默认True

        Returns:
            1 表示出现形态，0 表示未出现，None 表示数据不足

        Example:
            signal = api.get_qiming_star('600519.SH', '2026-03-01')
        """
        return get_qiming_star(code, date, use_adjusted)

    def get_evening_star(self, code: str, date: str, use_adjusted: bool = True) -> Optional[int]:
        """
        检测黄昏之星（Evening Star）形态。

        黄昏之星是顶部反转信号，与早晨之星相反：第一根大阳线、第二根十字星
        （开高收于阳线实体上方）、第三根大阴线并收回阳线实体一半以上。

        结果会缓存到 cached_signals 表，相同参数直接读缓存。

        Args:
            code: 股票代码
            date: 判断日期，格式 YYYY-MM-DD（以该日为第三根K线）
            use_adjusted: 是否使用后复权价格，默认True

        Returns:
            1 表示出现形态，0 表示未出现，None 表示数据不足

        Example:
            signal = api.get_evening_star('600519.SH', '2026-03-01')
        """
        return get_evening_star(code, date, use_adjusted)

    def get_huanghun_star(self, code: str, date: str, use_adjusted: bool = True) -> Optional[int]:
        """
        检测黄昏星形态（黄昏之星别名）。

        黄昏星即黄昏之星（Evening Star），共享同一缓存键 EVENING_STAR，
        结果与 get_evening_star 完全一致。

        Args:
            code: 股票代码
            date: 判断日期，格式 YYYY-MM-DD
            use_adjusted: 是否使用后复权价格，默认True

        Returns:
            1 表示出现形态，0 表示未出现，None 表示数据不足

        Example:
            signal = api.get_huanghun_star('600519.SH', '2026-03-01')
        """
        return get_huanghun_star(code, date, use_adjusted)

    def get_three_white_soldiers(self, code: str, date: str, use_adjusted: bool = True) -> Optional[int]:
        """
        检测红三兵（Three White Soldiers）形态。

        红三兵是强势上涨信号，由连续三根阳线构成，每根实体占比≥50%，
        上影线≤20%，且每根K线的开盘价在前一根实体范围内（逐步跳空上行）。

        结果会缓存到 cached_signals 表，相同参数直接读缓存。

        Args:
            code: 股票代码
            date: 判断日期，格式 YYYY-MM-DD（以该日为第三根K线）
            use_adjusted: 是否使用后复权价格，默认True

        Returns:
            1 表示出现形态，0 表示未出现，None 表示数据不足

        Example:
            signal = api.get_three_white_soldiers('600519.SH', '2026-03-01')
        """
        return get_three_white_soldiers(code, date, use_adjusted)

    def get_three_black_crows(self, code: str, date: str, use_adjusted: bool = True) -> Optional[int]:
        """
        检测三只乌鸦（Three Black Crows）形态。

        三只乌鸦是强势下跌信号，由连续三根阴线构成，每根实体占比≥50%，
        下影线≤20%，且每根K线的开盘价在前一根实体范围内（逐步跳空下行）。

        结果会缓存到 cached_signals 表，相同参数直接读缓存。

        Args:
            code: 股票代码
            date: 判断日期，格式 YYYY-MM-DD（以该日为第三根K线）
            use_adjusted: 是否使用后复权价格，默认True

        Returns:
            1 表示出现形态，0 表示未出现，None 表示数据不足

        Example:
            signal = api.get_three_black_crows('600519.SH', '2026-03-01')
        """
        return get_three_black_crows(code, date, use_adjusted)

    def get_dark_cloud_cover(self, code: str, date: str, use_adjusted: bool = True) -> Optional[int]:
        """
        检测乌云盖顶（Dark Cloud Cover）形态。

        乌云盖顶是顶部反转信号，由两根K线构成：第一根大阳线，第二根阴线
        高开（开盘高于前收）后下跌，收盘深入阳线实体一半以上但不低于阳线开盘。

        结果会缓存到 cached_signals 表，相同参数直接读缓存。

        Args:
            code: 股票代码
            date: 判断日期，格式 YYYY-MM-DD（以该日为第二根K线）
            use_adjusted: 是否使用后复权价格，默认True

        Returns:
            1 表示出现形态，0 表示未出现，None 表示数据不足

        Example:
            signal = api.get_dark_cloud_cover('600519.SH', '2026-03-01')
        """
        return get_dark_cloud_cover(code, date, use_adjusted)

    def get_rounding_bottom(self, code: str, date: str, period: int = 60, use_adjusted: bool = True) -> Optional[int]:
        """
        检测圆弧底（Rounding Bottom / Saucer）形态。

        圆弧底是长期底部反转形态，价格在 period 根K线内呈现 U 形走势：
        左侧缓慢下跌，底部盘整，右侧缓慢回升，最低点出现在中间三分之一区段。

        结果会缓存到 cached_signals 表，相同参数直接读缓存。

        Args:
            code: 股票代码
            date: 判断日期，格式 YYYY-MM-DD
            period: 观察窗口（K线根数），默认60
            use_adjusted: 是否使用后复权价格，默认True

        Returns:
            1 表示出现形态，0 表示未出现，None 表示数据不足

        Example:
            signal = api.get_rounding_bottom('600519.SH', '2026-03-01', 60)
        """
        return get_rounding_bottom(code, date, period, use_adjusted)

    def get_ascending_triangle(self, code: str, date: str, period: int = 30, use_adjusted: bool = True) -> Optional[int]:
        """
        检测上升三角形（Ascending Triangle）形态。

        上升三角形是整理后向上突破的形态：水平阻力位保持不变，
        支撑位持续上移（低点逐步抬高），是多头蓄力信号。

        结果会缓存到 cached_signals 表，相同参数直接读缓存。

        Args:
            code: 股票代码
            date: 判断日期，格式 YYYY-MM-DD
            period: 观察窗口（K线根数），默认30
            use_adjusted: 是否使用后复权价格，默认True

        Returns:
            1 表示出现形态，0 表示未出现，None 表示数据不足

        Example:
            signal = api.get_ascending_triangle('600519.SH', '2026-03-01', 30)
        """
        return get_ascending_triangle(code, date, period, use_adjusted)

    def get_top_pattern(self, code: str, date: str, period: int = 60, use_adjusted: bool = True) -> Optional[int]:
        """
        检测顶部形态（双顶 / M头）。

        顶部形态由两个相近高点和中间颈线构成：两个高点高度接近（误差在容忍范围内），
        颈线低点跌幅达到一定比例，当前价格已从第二高点回落，确认顶部。

        结果会缓存到 cached_signals 表，相同参数直接读缓存。

        Args:
            code: 股票代码
            date: 判断日期，格式 YYYY-MM-DD
            period: 观察窗口（K线根数），默认60
            use_adjusted: 是否使用后复权价格，默认True

        Returns:
            1 表示出现形态，0 表示未出现，None 表示数据不足

        Example:
            signal = api.get_top_pattern('600519.SH', '2026-03-01', 60)
        """
        return get_top_pattern(code, date, period, use_adjusted)

    # ============================================================
    # 性能指标类接口
    # ============================================================

    def get_max_drawdown(self, equity_curve: List[float]) -> tuple:
        """
        计算最大回撤。
        
        Args:
            equity_curve: 权益曲线，资产列表[初始值, ..., 最终值]
        
        Returns:
            元组 (最大回撤比例, 最高点索引, 最低点索引)
        
        Example:
            dd, peak_idx, drawdown_idx = api.get_max_drawdown([1000000, 1100000, 950000])
            print(f'最大回撤: {dd:.2%}')
        """
        return get_max_drawdown(equity_curve)

    def get_max_drawdown_pct(self, equity_curve: List[float]) -> float:
        """
        获取最大回撤百分比。
        
        Args:
            equity_curve: 权益曲线
        
        Returns:
            最大回撤比例，如 0.15 表示 15%
        """
        return get_max_drawdown_pct(equity_curve)

    def get_annualized_return(self, total_return: float, days: int) -> float:
        """
        计算年化收益率。
        
        Args:
            total_return: 总收益率，如 0.15 表示 15%
            days: 交易天数
        
        Returns:
            年化收益率
        
        Example:
            annualized = api.get_annualized_return(0.15, 60)
        """
        return get_annualized_return(total_return, days)

    def get_total_return(self, initial_value: float, final_value: float) -> float:
        """
        计算总收益率。
        
        Args:
            initial_value: 初始资金
            final_value: 最终资金
        
        Returns:
            总收益率
        """
        return get_total_return(initial_value, final_value)

    def get_sharpe_ratio(self, equity_curve: List[float], risk_free_rate: float = 0.03) -> float:
        """
        计算夏普比率。
        
        Args:
            equity_curve: 权益曲线
            risk_free_rate: 无风险利率(年化)，默认0.03
        
        Returns:
            夏普比率
        
        Example:
            sharpe = api.get_sharpe_ratio([1000000, 1050000, 1020000])
        """
        return get_sharpe_ratio(equity_curve, risk_free_rate)

    def get_win_rate(self, trades: List[Dict]) -> float:
        """
        计算胜率。
        
        Args:
            trades: 交易记录列表，每条包含 {'profit': 盈亏金额}
        
        Returns:
            胜率(0-100)
        
        Example:
            trades = [{'profit': 1000}, {'profit': -500}, {'profit': 800}]
            win_rate = api.get_win_rate(trades)
        """
        return get_win_rate(trades)

    def get_profit_loss_ratio(self, trades: List[Dict]) -> float:
        """
        计算盈亏比。
        
        Args:
            trades: 交易记录列表
        
        Returns:
            盈亏比（平均盈利/平均亏损）
        """
        return get_profit_loss_ratio(trades)

    def get_calmar_ratio(self, equity_curve: List[float], days: int) -> float:
        """
        计算卡尔玛比率（年化收益/最大回撤）。
        
        Args:
            equity_curve: 权益曲线
            days: 交易天数
        
        Returns:
            卡尔玛比率
        """
        return get_calmar_ratio(equity_curve, days)

    def get_volatility(self, equity_curve: List[float]) -> float:
        """
        计算收益波动率（年化）。
        
        Args:
            equity_curve: 权益曲线
        
        Returns:
            年化波动率
        """
        return get_volatility(equity_curve)

    def get_trade_stats(self, trades: List[Dict]) -> Dict:
        """
        获取交易统计信息。
        
        Args:
            trades: 交易记录列表
        
        Returns:
            统计信息字典，包含:
            - total_trades: 总交易次数
            - wins: 盈利次数
            - losses: 亏损次数
            - win_rate: 胜率
            - profit_loss_ratio: 盈亏比
            - total_profit: 总盈利
            - total_loss: 总亏损
            - avg_profit: 平均盈利
            - avg_loss: 平均亏损
        """
        return get_trade_stats(trades)

    def calculate_metrics(self, equity_curve: List[float], trades: List[Dict], initial_cash: float, days: int) -> Dict:
        """
        生成完整的回测报告。
        
        Args:
            equity_curve: 权益曲线
            trades: 交易记录列表
            initial_cash: 初始资金
            days: 交易天数
        
        Returns:
            回测报告字典，包含:
            - initial_cash: 初始资金
            - final_value: 最终资金
            - total_return: 总收益率
            - total_return_pct: 总收益率(%)
            - annualized_return: 年化收益率
            - annualized_return_pct: 年化收益率(%)
            - max_drawdown: 最大回撤
            - max_drawdown_pct: 最大回撤(%)
            - sharpe_ratio: 夏普比率
            - calmar_ratio: 卡尔玛比率
            - volatility: 波动率
            - trading_days: 交易天数
            - trade_stats: 交易统计
        
        Example:
            equity = [1000000, 1050000, 1020000]
            trades = [{'profit': 5000}, {'profit': -3000}]
            report = api.calculate_metrics(equity, trades, 1000000, 30)
            print(f"收益率: {report['total_return_pct']:.2f}%")
            print(f"夏普比率: {report['sharpe_ratio']:.2f}")
        """
        return generate_report(equity_curve, trades, initial_cash, days)

    # ============================================================
    # 回测工具类接口
    # ============================================================

    def simulate_trade(self, action: str, price: float, quantity: int, fee_rate: float = 0.0003) -> Dict:
        """
        模拟单笔交易，计算成本和手续费。
        
        Args:
            action: 交易方向，'BUY' 或 'SELL'
            price: 成交价格
            quantity: 成交数量
            fee_rate: 手续费率，默认0.0003(万三)
        
        Returns:
            字典 {'cost': 成本, 'fee': 手续费, 'net_proceeds': 净收款(卖出)}
        
        Example:
            result = api.simulate_trade('BUY', 100.0, 100)
            print(f"成本: {result['cost']}, 手续费: {result['fee']}")
        """
        return simulate_trade(action, price, quantity, fee_rate)

    def calculate_trade_cost(self, action: str, price: float, quantity: int, fee_rate: float = 0.0003, slippage: float = 0.0) -> float:
        """
        计算交易成本（含手续费和滑点）。
        
        Args:
            action: 交易方向
            price: 价格
            quantity: 数量
            fee_rate: 手续费率
            slippage: 滑点比例
        
        Returns:
            交易成本
        """
        return calculate_trade_cost(action, price, quantity, fee_rate, slippage)

    def create_position(self, code: str, shares: int, price: float, date: str) -> Position:
        """
        创建持仓对象。
        
        Args:
            code: 股票代码
            shares: 股数
            price: 买入价格
            date: 买入日期
        
        Returns:
            Position对象
        
        Example:
            pos = api.create_position('600519.SH', 100, 1800.0, '2026-01-01')
        """
        return create_position(code, shares, price, date)

    def get_position_value(self, position: Position, current_price: float) -> float:
        """
        计算持仓市值。
        
        Args:
            position: Position对象
            current_price: 当前价格
        
        Returns:
            市值
        """
        return get_position_value(position, current_price)

    def get_position_profit(self, position: Position, current_price: float) -> tuple:
        """
        计算持仓盈亏。
        
        Args:
            position: Position对象
            current_price: 当前价格
        
        Returns:
            元组 (盈亏金额, 盈亏比例)
        
        Example:
            profit, pct = api.get_position_profit(position, 2000.0)
            print(f"盈利: {profit}, 比例: {pct:.2%}")
        """
        return get_position_profit(position, current_price)

    def calculate_portfolio_value(self, cash: float, positions: Dict[str, Position], prices: Dict[str, float]) -> float:
        """
        计算组合总价值。
        
        Args:
            cash: 现金
            positions: 持仓字典 {code: Position}
            prices: 当前价格字典 {code: price}
        
        Returns:
            总资产
        
        Example:
            value = api.calculate_portfolio_value(500000, positions, current_prices)
        """
        return calculate_portfolio_value(cash, positions, prices)

    def get_portfolio_positions(self, positions: Dict[str, Position]) -> List[Dict]:
        """
        获取组合持仓详情列表。
        
        Args:
            positions: 持仓字典
        
        Returns:
            持仓详情列表
        """
        return get_portfolio_positions(positions)

    def build_equity_curve(self, daily_values: List[tuple]) -> List[float]:
        """
        从每日资产构建权益曲线。
        
        Args:
            daily_values: [(日期, 资产), ...] 按日期升序
        
        Returns:
            权益曲线列表
        
        Example:
            values = [('2026-01-01', 1000000), ('2026-01-02', 1005000)]
            curve = api.build_equity_curve(values)
        """
        return build_equity_curve(daily_values)

    def calculate_daily_returns(self, equity_curve: List[float]) -> List[float]:
        """
        计算日收益率序列。
        
        Args:
            equity_curve: 权益曲线
        
        Returns:
            日收益率列表
        """
        return calculate_daily_returns(equity_curve)

    def should_buy(self, current_price: float, ma_short: float, ma_long: float, rsi: float = 50, rsi_oversold: float = 30) -> bool:
        """
        买入信号判断（MA金叉 + RSI超卖）。
        
        Args:
            current_price: 当前价格
            ma_short: 短期均线
            ma_long: 长期均线
            rsi: RSI值
            rsi_oversold: RSI超卖阈值
        
        Returns:
            是否买入
        
        Example:
            if api.should_buy(close, ma5, ma20, rsi, 30):
                print('买入信号')
        """
        return should_buy(current_price, ma_short, ma_long, rsi, rsi_oversold)

    def should_sell(self, current_price: float, ma_short: float, ma_long: float, rsi: float = 50, rsi_overbought: float = 70) -> bool:
        """
        卖出信号判断（MA死叉或RSI超买）。
        
        Args:
            current_price: 当前价格
            ma_short: 短期均线
            ma_long: 长期均线
            rsi: RSI值
            rsi_overbought: RSI超买阈值
        
        Returns:
            是否卖出
        
        Example:
            if api.should_sell(close, ma5, ma20, rsi, 70):
                print('卖出信号')
        """
        return should_sell(current_price, ma_short, ma_long, rsi, rsi_overbought)

    def calculate_drawdown(self, equity_curve: List[float]) -> List[float]:
        """
        计算回撤序列。
        
        Args:
            equity_curve: 权益曲线
        
        Returns:
            回撤序列列表
        
        Example:
            drawdowns = api.calculate_drawdown([1000000, 1100000, 950000])
        """
        return calculate_drawdown(equity_curve)

    # ============================================================
    # Tick级数据接口（模拟级Tick）
    # ============================================================

    def get_tick_data(self, code: str, date: str) -> Optional[Dict]:
        """
        获取指定日期的Tick级数据（模拟级）。
        
        Args:
            code: 股票代码
            date: 日期，格式 YYYY-MM-DD
        
        Returns:
            Tick数据字典，包含:
            - time: 时间
            - open: 开盘价
            - high: 最高价
            - low: 最低价
            - close: 收盘价
            - volume: 成交量
            - amount: 成交额
            若无数据返回None
        
        Example:
            tick = api.get_tick_data('600519.SH', '2026-03-01')
        """
        klines = query_daily_kline(codes=[code], start_date=date, end_date=date, order_by="date ASC")
        if not klines:
            return None
        k = klines[0]
        return {
            'time': k.date,
            'open': k.open,
            'high': k.high,
            'low': k.low,
            'close': k.close,
            'volume': k.volume,
            'amount': k.amount,
        }

    def get_realtime_bar(self, code: str, date: str) -> Dict:
        """
        获取实时Bar数据（用于实盘级Tick）。
        
        Args:
            code: 股票代码
            date: 日期
        
        Returns:
            Bar数据字典
        
        Example:
            bar = api.get_realtime_bar('600519.SH', '2026-03-01')
        """
        return self.get_tick_data(code, date)

    # ============================================================
    # 订单管理接口
    # ============================================================

    def create_order(self, code: str, action: str, price: float, quantity: int) -> Dict:
        """
        创建订单（本地模拟，非真实下单）。
        
        Args:
            code: 股票代码
            action: 'BUY' 或 'SELL'
            price: 价格
            quantity: 数量（股）
        
        Returns:
            订单字典，包含:
            - order_id: 订单ID
            - code: 股票代码
            - action: 方向
            - price: 价格
            - quantity: 数量
            - status: 状态 'PENDING'
            - create_time: 创建时间
        
        Example:
            order = api.create_order('600519.SH', 'BUY', 1800.0, 100)
        """
        import time
        return {
            'order_id': f"ORDER_{int(time.time()*1000)}",
            'code': code,
            'action': action.upper(),
            'price': price,
            'quantity': quantity,
            'status': 'PENDING',
            'create_time': time.strftime('%Y-%m-%d %H:%M:%S'),
        }

    def cancel_order(self, order: Dict) -> bool:
        """
        取消订单。
        
        Args:
            order: 订单字典
        
        Returns:
            是否取消成功
        
        Example:
            api.cancel_order(order)
        """
        if order.get('status') == 'PENDING':
            order['status'] = 'CANCELLED'
            return True
        return False

    def get_order_status(self, order: Dict) -> str:
        """
        获取订单状态。
        
        Args:
            order: 订单字典
        
        Returns:
            状态: PENDING, FILLED, CANCELLED, REJECTED
        
        Example:
            status = api.get_order_status(order)
        """
        return order.get('status', 'UNKNOWN')



    def close_position(self, position: Position, price: float, date: str) -> Dict:
        """
        平仓（卖出股票结束多头持仓）。
        
        Args:
            position: Position对象
            price: 平仓价格
            date: 平仓日期
        
        Returns:
            平仓结果字典，包含:
            - profit: 盈亏金额
            - profit_pct: 盈亏比例
            - hold_days: 持有天数
        
        Example:
            result = api.close_position(position, 1900.0, '2026-01-15')
            print(f"盈利: {result['profit']}")
        """
        profit, profit_pct = get_position_profit(position, price)
        hold_days = (date_to_num(date) - date_to_num(position.entry_date))
        return {
            'profit': profit,
            'profit_pct': profit_pct,
            'hold_days': hold_days,
        }

    def update_position_price(self, position: Position, current_price: float) -> None:
        """
        更新持仓的当前价格（用于市价计算）。
        
        Args:
            position: Position对象
            current_price: 当前价格
        """
        update_position(position, current_price)

    # ============================================================
    # 回测引擎控制接口
    # ============================================================

    def init_backtest(self, initial_cash: float = 1000000.0, fee_rate: float = 0.0003) -> Dict:
        """
        初始化回测环境。
        
        Args:
            initial_cash: 初始资金，默认100万
            fee_rate: 手续费率，默认万三
        
        Returns:
            回测环境字典
        
        Example:
            env = api.init_backtest(1000000, 0.0003)
        """
        return {
            'initial_cash': initial_cash,
            'fee_rate': fee_rate,
            'cash': initial_cash,
            'positions': {},
            'orders': [],
            'trades': [],
            'equity_curve': [],
        }

    def execute_buy(self, env: Dict, code: str, price: float, quantity: int, date: str) -> Dict:
        """
        执行买入操作。
        
        Args:
            env: 回测环境字典
            code: 股票代码
            price: 价格
            quantity: 数量
            date: 交易日期
        
        Returns:
            执行结果字典
        """
        fee_rate = env.get('fee_rate', 0.0003)
        new_cash, new_positions, result = buy(
            env['cash'], env['positions'], code, price, quantity, date, fee_rate
        )
        
        env['cash'] = new_cash
        env['positions'] = new_positions
        
        if result.success:
            env['trades'].append({
                'code': code,
                'action': 'BUY',
                'price': price,
                'quantity': quantity,
                'cost': result.cost,
                'fee': result.fee,
            })
        
        return {
            'success': result.success,
            'code': code,
            'action': 'BUY',
            'price': price,
            'quantity': quantity,
            'cost': result.cost if result.success else 0,
            'fee': result.fee if result.success else 0,
            'reason': result.reason,
        }

    def execute_sell(self, env: Dict, code: str, price: float, quantity: int) -> Dict:
        """
        执行卖出操作。
        
        Args:
            env: 回测环境字典
            code: 股票代码
            price: 价格
            quantity: 数量
        
        Returns:
            执行结果字典
        """
        fee_rate = env.get('fee_rate', 0.0003)
        new_cash, new_positions, result = sell(
            env['cash'], env['positions'], code, price, quantity, fee_rate
        )
        
        env['cash'] = new_cash
        env['positions'] = new_positions
        
        if result.success:
            env['trades'].append({
                'code': code,
                'action': 'SELL',
                'price': price,
                'quantity': quantity,
                'net_proceeds': result.net_proceeds,
                'fee': result.fee,
            })
        
        return {
            'success': result.success,
            'code': code,
            'action': 'SELL',
            'price': price,
            'quantity': quantity,
            'net_proceeds': result.net_proceeds if result.success else 0,
            'fee': result.fee if result.success else 0,
            'reason': result.reason,
        }



    def get_equity(self, env: Dict, current_prices: Dict[str, float]) -> float:
        """
        获取当前权益（现金+持仓市值）。
        
        Args:
            env: 回测环境字典
            current_prices: 当前价格字典 {code: price}
        
        Returns:
            总权益
        """
        return calculate_portfolio_value(env['cash'], env['positions'], current_prices)

    def record_equity(self, env: Dict, date: str, current_prices: Dict[str, float]) -> None:
        """
        记录每日权益到权益曲线。
        
        Args:
            env: 回测环境字典
            date: 日期
            current_prices: 当前价格字典
        """
        equity = self.get_equity(env, current_prices)
        env['equity_curve'].append((date, equity))

    # ============================================================
    # 策略辅助函数
    # ============================================================

    def get_price_change_rate(self, code: str, date: str, days: int = 3) -> Optional[float]:
        """
        计算近N日平均涨幅。
        
        Args:
            code: 股票代码
            date: 日期
            days: 天数，默认3
        
        Returns:
            平均涨跌幅(%)，若数据不足返回None
        
        Example:
            avg_change = api.get_price_change_rate('600519.SH', '2026-03-01', 3)
        """
        import datetime
        start_dt = datetime.datetime.strptime(date, '%Y-%m-%d')
        end_dt = start_dt - datetime.timedelta(days=days * 2)
        start = end_dt.strftime('%Y-%m-%d')
        
        klines = query_daily_kline(codes=[code], start_date=start, end_date=date, order_by="date ASC")
        if len(klines) < days:
            return None
        
        klines.sort(key=lambda x: x.date, reverse=True)
        pct_sum = sum(k.pctChg for k in klines[:days])
        return pct_sum / days

    def get_top_performers(self, codes: List[str], date: str, days: int = 3, top_n: int = 3) -> List[tuple]:
        """
        获取近N日涨幅最高的股票。
        
        Args:
            codes: 股票代码列表
            date: 日期
            days: 计算天数
            top_n: 返回前N只
        
        Returns:
            [(股票代码, 平均涨幅), ...] 按涨幅降序
        
        Example:
            top_stocks = api.get_top_performers(codes, '2026-03-01', 3, 3)
        """
        results = []
        for code in codes:
            avg_change = self.get_price_change_rate(code, date, days)
            if avg_change is not None:
                results.append((code, avg_change))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_n]

    def get_price_at_date(self, code: str, date: str) -> Optional[float]:
        """
        获取指定日期的收盘价。
        
        Args:
            code: 股票代码
            date: 日期
        
        Returns:
            收盘价，若无数据返回None
        
        Example:
            price = api.get_price_at_date('600519.SH', '2026-03-01')
        """
        klines = query_daily_kline(codes=[code], start_date=date, end_date=date, order_by="date ASC")
        return klines[0].close if klines else None

    def get_prices_at_dates(self, code: str, dates: List[str]) -> List[Optional[float]]:
        """
        获取多个日期的收盘价。
        
        Args:
            code: 股票代码
            dates: 日期列表
        
        Returns:
            收盘价列表（按日期升序）
        
        Example:
            prices = api.get_prices_at_dates('600519.SH', ['2026-01-01', '2026-01-02'])
        """
        if not dates:
            return []
        
        start = dates[0]
        end = dates[-1]
        klines = query_daily_kline(codes=[code], start_date=start, end_date=end, order_by="date ASC")
        
        price_map = {k.date: k.close for k in klines}
        return [price_map.get(d) for d in dates]

    # ============================================================
    # 数据库维护接口
    # ============================================================

    def init_databases(self) -> None:
        """
        初始化所有数据库（指标库等）。
        
        Example:
            api.init_databases()
        """
        init_indicators_db()

    def clear_indicator_cache(self, code: str = None) -> None:
        """
        清除技术指标缓存。
        
        Args:
            code: 股票代码，None表示清除所有
        
        Example:
            api.clear_indicator_cache('600519.SH')  # 清除指定股票
            api.clear_indicator_cache()  # 清除所有
        """
        from indicators import _get_conn
        conn = _get_conn()
        try:
            if code:
                conn.execute("DELETE FROM indicators WHERE code=?", (code,))
            else:
                conn.execute("DELETE FROM indicators")
            conn.commit()
        finally:
            conn.close()


def date_to_num(date_str: str) -> int:
    """日期字符串转数字（用于计算天数差）"""
    import datetime
    try:
        return int(datetime.datetime.strptime(date_str, '%Y-%m-%d').strftime('%Y%m%d'))
    except:
        return 0


if __name__ == "__main__":
    api = StockApi()
    print("StockApi 初始化完成")
