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
from typing import Optional, List, Dict, Union

sys.path.insert(0, __file__.rsplit('/', 1)[0])
from sqlalchemy import text
from db_engine import getEngine
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
    query_sector_stock_map,
    query_top_list,
    query_top_inst,
    query_sector_flow_daily,
    query_index_basic,
    query_index_daily,
    query_index_weekly,
    query_index_monthly,
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
    SectorStockMap,
    TopList,
    TopInst,
    SectorFlowDaily,
    IndexBasic,
    IndexDaily,
    IndexWeekly,
    IndexMonthly,
    AppVersion,
    TokenCheckResult
)


from formulaicAlphas import AlphaDataLoader, Alpha101, ALPHA_DESCRIPTIONS

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
    get_bomb_board,
    get_bomb_board_count,
    get_consecutive_limit_up,
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
import remote_api,data_fetcher,utils, config

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
    # 工具类
    # ============================================================

    def get_user_token() -> str:
        """
        获取用户当前token
        返回值: 用户token
        """
        return config.get_token()
    
    def set_user_token(self, token: str):
        """
        设置用户当前token
        参数:
            token 设置的token
        """
        return config.set_token(token=token)

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

    def get_sector_stock_map(
        self,
        sector_codes: List[str] = [],
        stock_codes: List[str] = [],
        source: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[SectorStockMap]:
        """
        查询板块成分股映射列表

        参数:
            sector_codes 按板块代码列表过滤
            stock_codes  按股票代码列表过滤
            source       按数据来源精确过滤
            limit        返回最大记录数；为 None 表示不限
            offset       分页偏移量，默认 0

        示例:
            # 查询某个板块下的所有股票
            records = api.get_sector_stock_map(sector_codes=["BK0475"])

            # 查询某只股票归属的所有板块
            records = api.get_sector_stock_map(stock_codes=["000001.SZ"])
        """
        return query_sector_stock_map(
            sector_codes=sector_codes,
            stock_codes=stock_codes,
            source=source,
            limit=limit,
            offset=offset,
        )

    def get_top_list(
        self,
        ts_codes: List[str] = [],
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        order_by: str = "trade_date ASC",
    ) -> List[TopList]:
        """
        查询龙虎榜每日明细列表

        参数:
            ts_codes    按股票代码列表过滤
            trade_date  按具体交易日期精确过滤，格式 "YYYY-MM-DD"
            start_date  按日期范围过滤下限（含），格式 "YYYY-MM-DD"
            end_date    按日期范围过滤上限（含），格式 "YYYY-MM-DD"
            limit       返回最大记录数；为 None 表示不限
            offset      分页偏移量，默认 0
            order_by    排序表达式，默认 "trade_date ASC"

        示例:
            # 查询某天龙虎榜数据
            records = api.get_top_list(trade_date="2024-06-03")

            # 查询某只股票历史上榜记录
            records = api.get_top_list(ts_codes=["000001.SZ"])
        """
        return query_top_list(
            ts_codes=ts_codes,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
            order_by=order_by,
        )

    def get_top_inst(
        self,
        ts_codes: List[str] = [],
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        side: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        order_by: str = "trade_date ASC",
    ) -> List[TopInst]:
        """
        查询龙虎榜机构交易明细列表

        参数:
            ts_codes    按股票代码列表过滤
            trade_date  按具体交易日期精确过滤，格式 "YYYY-MM-DD"
            start_date  按日期范围过滤下限（含），格式 "YYYY-MM-DD"
            end_date    按日期范围过滤上限（含），格式 "YYYY-MM-DD"
            side        按买卖类型过滤（"0"=买入最大的前5名, "1"=卖出最大的前5名）
            limit       返回最大记录数；为 None 表示不限
            offset      分页偏移量，默认 0
            order_by    排序表达式，默认 "trade_date ASC"

        示例:
            # 查询某天机构交易明细
            records = api.get_top_inst(trade_date="2024-06-03")

            # 查询某只股票历史机构上榜记录
            records = api.get_top_inst(ts_codes=["000001.SZ"])
        """
        return query_top_inst(
            ts_codes=ts_codes,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date,
            side=side,
            limit=limit,
            offset=offset,
            order_by=order_by,
        )

    def get_sector_flow_daily(
        self,
        ts_codes: List[str] = [],
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        order_by: str = "trade_date ASC",
    ) -> List[SectorFlowDaily]:
        """
        查询板块资金流向列表

        参数:
            ts_codes     按板块代码列表过滤
            trade_date   按具体交易日期精确过滤，格式 "YYYY-MM-DD"
            start_date   按日期范围过滤下限（含），格式 "YYYY-MM-DD"
            end_date     按日期范围过滤上限（含），格式 "YYYY-MM-DD"
            limit        返回最大记录数；为 None 表示不限
            offset       分页偏移量，默认 0
            order_by     排序表达式，默认 "trade_date ASC"

        示例:
            # 查询某天所有板块资金流向
            records = api.get_sector_flow_daily(trade_date="2024-06-03")

            # 查询某个板块历史资金流向
            records = api.get_sector_flow_daily(ts_codes=["BK0475"])
        """
        return query_sector_flow_daily(
            ts_codes=ts_codes,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
            order_by=order_by,
        )

    def get_index_basic(
        self,
        ts_code: Optional[str] = None,
        market: Optional[str] = None,
        publisher: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[IndexBasic]:
        """
        查询指数基础信息列表

        参数:
            ts_code   按指数代码精确过滤
            market    按市场精确过滤
            publisher 按发布方精确过滤
            limit     返回最大记录数；为 None 表示不限
            offset    分页偏移量，默认 0

        示例:
            # 查询所有指数
            records = api.get_index_basic()

            # 查询上证指数信息
            records = api.get_index_basic(ts_code="000001.SH")
        """
        return query_index_basic(
            ts_code=ts_code,
            market=market,
            publisher=publisher,
            limit=limit,
            offset=offset,
        )

    def get_index_daily(
        self,
        ts_codes: List[str] = [],
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        order_by: str = "trade_date ASC",
    ) -> List[IndexDaily]:
        """
        查询指数日线行情列表

        参数:
            ts_codes    按指数代码列表过滤
            trade_date  按具体交易日期精确过滤，格式 "YYYY-MM-DD"
            start_date  按日期范围过滤下限（含），格式 "YYYY-MM-DD"
            end_date    按日期范围过滤上限（含），格式 "YYYY-MM-DD"
            limit       返回最大记录数；为 None 表示不限
            offset      分页偏移量，默认 0
            order_by    排序表达式，默认 "trade_date ASC"

        示例:
            # 查询上证指数历史日线
            records = api.get_index_daily(ts_codes=["000001.SH"])

            # 查询某天所有指数行情
            records = api.get_index_daily(trade_date="2024-06-03")
        """
        return query_index_daily(
            ts_codes=ts_codes,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
            order_by=order_by,
        )

    def get_index_weekly(
        self,
        ts_codes: List[str] = [],
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        order_by: str = "trade_date ASC",
    ) -> List[IndexWeekly]:
        """
        查询指数周线行情列表

        参数:
            ts_codes    按指数代码列表过滤
            trade_date  按具体日期精确过滤，格式 "YYYY-MM-DD"
            start_date  按日期范围过滤下限（含），格式 "YYYY-MM-DD"
            end_date    按日期范围过滤上限（含），格式 "YYYY-MM-DD"
            limit       返回最大记录数；为 None 表示不限
            offset      分页偏移量，默认 0
            order_by    排序表达式，默认 "trade_date ASC"

        示例:
            # 查询上证指数周线
            records = api.get_index_weekly(ts_codes=["000001.SH"])
        """
        return query_index_weekly(
            ts_codes=ts_codes,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
            order_by=order_by,
        )

    def get_index_monthly(
        self,
        ts_codes: List[str] = [],
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        order_by: str = "trade_date ASC",
    ) -> List[IndexMonthly]:
        """
        查询指数月线行情列表

        参数:
            ts_codes    按指数代码列表过滤
            trade_date  按具体日期精确过滤，格式 "YYYY-MM-DD"
            start_date  按日期范围过滤下限（含），格式 "YYYY-MM-DD"
            end_date    按日期范围过滤上限（含），格式 "YYYY-MM-DD"
            limit       返回最大记录数；为 None 表示不限
            offset      分页偏移量，默认 0
            order_by    排序表达式，默认 "trade_date ASC"

        示例:
            # 查询上证指数月线
            records = api.get_index_monthly(ts_codes=["000001.SH"])
        """
        return query_index_monthly(
            ts_codes=ts_codes,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date,
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

    def get_mass(self, code: str, date: str, period: int = 25, use_adjusted: bool = True) -> Optional[float]:
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
        return get_mass(code, date, period, use_adjusted)

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

    def get_bomb_board(self, code: str, date: str) -> Optional[int]:
        """
        判断指定日期是否发生炸板（曾涨停但收盘未封板）。

        炸板意味着多头动能不足，当日虽冲击涨停但尾盘筹码松动，
        可作为规避追高或观察多空博弈的参考信号。

        不使用复权价格——炸板基于市场实际涨停价判断。

        Args:
            code: 股票代码
            date: 判断日期，格式 YYYY-MM-DD

        Returns:
            1=当日炸板，0=当日未炸板，None=非交易日或数据缺失

        Example:
            is_bomb = api.get_bomb_board('000001.SZ', '2026-03-01')
        """
        return get_bomb_board(code, date)

    def get_bomb_board_count(self, code: str, date: str, period: int = 20) -> Optional[int]:
        """
        统计近N个交易日内的炸板次数。

        炸板频繁说明个股多次冲板失败，多头信心不足；高频炸板的股票追高风险较大，
        可结合连板数综合评估封板质量。

        不使用复权价格——炸板基于市场实际涨停价判断。

        Args:
            code: 股票代码
            date: 统计截止日期，格式 YYYY-MM-DD
            period: 回溯交易日天数，默认20

        Returns:
            近period个交易日内炸板次数（int ≥ 0），数据不足时返回None

        Example:
            cnt = api.get_bomb_board_count('000001.SZ', '2026-03-01', 20)
        """
        return get_bomb_board_count(code, date, period)

    def get_consecutive_limit_up(self, code: str, date: str) -> Optional[int]:
        """
        获取截至指定日期的连续涨停天数（连板数）。

        直接读取数据源维护的 limit_streak 字段，含一字板等特殊情形，
        比自行计算更准确。连板数 >= 3 通常视为强势股，高连板存在高位风险。

        不使用复权价格——涨停判断基于市场实际价格。

        Args:
            code: 股票代码
            date: 判断日期，格式 YYYY-MM-DD

        Returns:
            连板数（int ≥ 0，0表示当日未涨停），非交易日或数据缺失返回None

        Example:
            streak = api.get_consecutive_limit_up('000001.SZ', '2026-03-01')
        """
        return get_consecutive_limit_up(code, date)

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
    # 复合筛选与分析类接口
    # ============================================================

    def get_stocks_by_industry_keyword(
        self,
        keyword: str,
        market: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[StockBasic]:
        """
        按行业关键词模糊搜索股票（industry LIKE %keyword%）。

        支持不精确的行业名称，如"半导体"可匹配"半导体及元件"、"集成电路"等。
        可叠加 market 过滤（主板/创业板/科创板）。

        Args:
            keyword: 行业关键词，如"半导体"、"芯片"、"银行"、"新能源"
            market: 市场类型过滤，如"主板"、"创业板"、"科创板"，None 表示不限
            limit: 最大返回数量，None 表示不限

        Returns:
            匹配的 StockBasic 列表

        Example:
            chip = api.get_stocks_by_industry_keyword('半导体')
            kechuang = api.get_stocks_by_industry_keyword('半导体', market='科创板')
        """
        return query_stock_basic(industry_keyword=keyword, market=market, limit=limit)

    def get_latest_income(self, code: str) -> Optional[Income]:
        """
        获取股票最新一期财务数据（合并报表）。

        从 income 表取 end_date 最新的一条合并报表记录，
        包含 ROE、ROA、毛利率、净利率、净利润增速等常用财务指标。

        Args:
            code: 股票代码，如 '000001.SZ'

        Returns:
            最新一期 Income 对象，无数据返回 None

        Example:
            inc = api.get_latest_income('600519.SH')
            print(f"ROE={inc.roe:.2f}%  毛利率={inc.gross_margin:.2f}%")
        """
        records = query_income(ts_codes=[code], report_type="1",
                               order_by="end_date DESC", limit=1)
        return records[0] if records else None

    def filter_stocks_by_fundamentals(
        self,
        date: str,
        pe_ttm_max: Optional[float] = None,
        roe_min: Optional[float] = None,
        mv_min_yi: Optional[float] = None,
        top_n: Optional[int] = None,
        order_by: str = "total_mv DESC",
    ) -> List[Dict]:
        """
        按基本面条件多维筛选股票，支持 PE/ROE/市值三重过滤。

        跨 daily_basic（PE、市值）与 income（ROE）两张表联合筛选，
        全部过滤在 Python 侧完成，结果按指定字段排序后返回。

        pe_ttm <= 0（亏损股）始终被排除在外。

        Args:
            date: 基本面数据日期，格式 YYYY-MM-DD（取当日 daily_basic 快照）
            pe_ttm_max: PE(TTM) 上限（不含），None 表示不过滤
            roe_min: ROE 下限（%，不含），None 表示不过滤
            mv_min_yi: 总市值下限（亿元），None 表示不过滤
            top_n: 最终返回数量，None 表示全部
            order_by: 排序字段，可选 'total_mv DESC'/'pe_ttm ASC'/'roe DESC' 等

        Returns:
            字典列表，每项含 ts_code / pe_ttm / total_mv_yi / roe（亿元，roe 仅在
            roe_min 不为 None 时出现），按 order_by 排序后取前 top_n 条

        Example:
            results = api.filter_stocks_by_fundamentals(
                '2026-03-14', pe_ttm_max=20, roe_min=15, mv_min_yi=100, top_n=20
            )
            for r in results:
                print(r['ts_code'], r['pe_ttm'], r['total_mv_yi'], r.get('roe'))
        """
        # ── Step 1: 全市场当日基本面快照 ───────────────────────────────────
        basics = query_daily_basic(trade_date=date)
        if not basics:
            return []

        # ── Step 2: PE + 市值过滤（数据来源 daily_basic）───────────────────
        mv_min_wan = (mv_min_yi * 10000) if mv_min_yi is not None else None
        candidates = []
        for b in basics:
            if b.pe_ttm <= 0:                  # 亏损股排除
                continue
            if pe_ttm_max is not None and b.pe_ttm > pe_ttm_max:
                continue
            if mv_min_wan is not None and b.total_mv < mv_min_wan:
                continue
            candidates.append(b)

        # ── Step 3: ROE 过滤（数据来源 income，批量查询后 Python 聚合）─────
        if roe_min is not None and candidates:
            codes = [b.ts_code for b in candidates]
            all_income = query_income(ts_codes=codes, report_type="1")
            # 每只股票取 end_date 最新的一期
            latest: Dict[str, Income] = {}
            for inc in sorted(all_income, key=lambda x: x.end_date):
                latest[inc.ts_code] = inc
            result = []
            for b in candidates:
                inc = latest.get(b.ts_code)
                if inc is None or inc.roe < roe_min:
                    continue
                result.append({
                    'ts_code':     b.ts_code,
                    'pe_ttm':      b.pe_ttm,
                    'total_mv_yi': round(b.total_mv / 10000, 2),
                    'roe':         inc.roe,
                })
        else:
            result = [{
                'ts_code':     b.ts_code,
                'pe_ttm':      b.pe_ttm,
                'total_mv_yi': round(b.total_mv / 10000, 2),
            } for b in candidates]

        # ── Step 4: 排序 + 截取 ────────────────────────────────────────────
        field_map = {
            'total_mv':     'total_mv_yi',
            'total_mv_yi':  'total_mv_yi',
            'pe_ttm':       'pe_ttm',
            'roe':          'roe',
        }
        parts = order_by.strip().split()
        sort_key   = field_map.get(parts[0].lower(), 'total_mv_yi')
        descending = len(parts) < 2 or parts[1].upper() == 'DESC'
        result.sort(key=lambda x: x.get(sort_key) or 0, reverse=descending)

        return result[:top_n] if top_n is not None else result

    def scan_all_signals(
        self,
        signal_type: str,
        date: str,
        period: int = 0,
        use_adjusted: bool = True,
        codes: Optional[List[str]] = None,
    ) -> Dict[str, int]:
        """
        全市场（或指定股票池）扫描指定裸K形态信号。

        对每只股票调用对应信号函数，返回所有触发信号（值=1）的股票代码→信号值字典。
        结果已缓存到 cached_signals 表，重复扫描同一日期无额外计算开销。

        Args:
            signal_type: 信号类型，不区分大小写，可选值：
                MORNING_STAR / QIMING_STAR / EVENING_STAR / HUANGHUN_STAR /
                THREE_WHITE_SOLDIERS / THREE_BLACK_CROWS / DARK_CLOUD_COVER /
                ROUNDING_BOTTOM / ASCENDING_TRIANGLE / TOP_PATTERN
            date: 扫描日期，格式 YYYY-MM-DD
            period: 窗口周期（仅对 ROUNDING_BOTTOM/ASCENDING_TRIANGLE/TOP_PATTERN 有效），
                    0 表示使用各信号默认值（60/30/60）
            use_adjusted: 是否使用后复权价格，默认 True
            codes: 待扫描股票代码列表，None 表示全市场扫描

        Returns:
            Dict[str, int]：{股票代码: 1}，仅包含信号值为 1 的股票；
            若某股票数据不足（返回 None）则不计入结果

        Example:
            hits = api.scan_all_signals('EVENING_STAR', '2026-03-14')
            print(f"黄昏之星: {list(hits.keys())}")

            hits = api.scan_all_signals('ROUNDING_BOTTOM', '2026-03-14', period=60)
        """
        _DISPATCH: Dict[str, any] = {
            'MORNING_STAR':        lambda c: get_morning_star(c, date, use_adjusted),
            'QIMING_STAR':         lambda c: get_qiming_star(c, date, use_adjusted),
            'EVENING_STAR':        lambda c: get_evening_star(c, date, use_adjusted),
            'HUANGHUN_STAR':       lambda c: get_huanghun_star(c, date, use_adjusted),
            'THREE_WHITE_SOLDIERS':lambda c: get_three_white_soldiers(c, date, use_adjusted),
            'THREE_BLACK_CROWS':   lambda c: get_three_black_crows(c, date, use_adjusted),
            'DARK_CLOUD_COVER':    lambda c: get_dark_cloud_cover(c, date, use_adjusted),
            'ROUNDING_BOTTOM':     lambda c: get_rounding_bottom(c, date, period or 60, use_adjusted),
            'ASCENDING_TRIANGLE':  lambda c: get_ascending_triangle(c, date, period or 30, use_adjusted),
            'TOP_PATTERN':         lambda c: get_top_pattern(c, date, period or 60, use_adjusted),
        }
        fn = _DISPATCH.get(signal_type.upper())
        if fn is None:
            raise ValueError(
                f"未知 signal_type: {signal_type!r}。"
                f"可选值: {list(_DISPATCH.keys())}"
            )
        scan_codes = codes if codes is not None else self.get_all_symbols()
        return {code: 1 for code in scan_codes if fn(code) == 1}

    def get_period_return(
        self,
        code: str,
        start_date: str,
        end_date: str,
        use_adjusted: bool = True,
    ) -> Optional[float]:
        """
        计算股票在指定区间内的期间收益率（%）。

        取区间内第一个和最后一个有效交易日的收盘价，使用后复权价格消除分红/送股影响。

        Args:
            code: 股票代码，如 '600519.SH'
            start_date: 区间起始日期，格式 YYYY-MM-DD（取当日或之后第一个交易日）
            end_date: 区间结束日期，格式 YYYY-MM-DD（取当日或之前最后一个交易日）
            use_adjusted: 是否使用后复权价格，默认 True

        Returns:
            收益率（%，保留4位小数），区间内交易日不足2天返回 None

        Example:
            ret = api.get_period_return('600519.SH', '2026-01-01', '2026-03-14')
            print(f"贵州茅台近3个月收益率: {ret:.2f}%")
        """
        klines = query_daily_kline(
            codes=[code], start_date=start_date, end_date=end_date,
            order_by="date ASC",
        )
        if len(klines) < 2:
            return None

        if use_adjusted:
            basics = query_daily_basic(
                ts_codes=[code],
                start_date=klines[0].date,
                end_date=klines[-1].date,
            )
            adj_map = {b.trade_date: b.adj_factor for b in basics}
            adj_s = adj_map.get(klines[0].date, 1.0)
            adj_e = adj_map.get(klines[-1].date, 1.0)
            close_s = klines[0].close * adj_s
            close_e = klines[-1].close * adj_e
        else:
            close_s = klines[0].close
            close_e = klines[-1].close

        if close_s == 0:
            return None
        return round((close_e - close_s) / close_s * 100, 4)

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
        with getEngine().connect() as conn:
            if code:
                conn.execute(text("DELETE FROM cached_indicators WHERE code=:code"), {"code": code})
            else:
                conn.execute(text("DELETE FROM cached_indicators"))
            conn.commit()

    # ── Alpha101 因子接口 ────────────────────────────────────────────────────

    def load_alpha_data(
        self,
        codes: List[str],
        start_date: str,
        end_date: str,
        fill_method: str = "ffill",
    ) -> dict:
        """
        加载 Alpha 因子计算所需的面板数据。

        Args:
            codes:       股票代码列表，如 ['000001.SZ', '600519.SH']
            start_date:  起始日期，格式 'YYYY-MM-DD'
            end_date:    截止日期，格式 'YYYY-MM-DD'
            fill_method: 缺失值填充方式（'ffill' / 'bfill' / None）

        Returns:
            字典，key 为字段名，value 为 DataFrame（行=日期，列=股票代码）：
              open, high, low, close, volume, amount, vwap, returns, ind

        Example:
            data = api.load_alpha_data(['000001.SZ', '600519.SH'], '2025-01-01', '2026-03-01')
        """
        loader = AlphaDataLoader()
        return loader.load(codes=codes, start_date=start_date, end_date=end_date, fill_method=fill_method)

    def compute_alpha(
        self,
        codes: List[str],
        start_date: str,
        end_date: str,
        alpha_num: int,
        fill_method: str = "ffill",
    ):
        """
        计算单个 Alpha 因子面板。

        Args:
            codes:      股票代码列表
            start_date: 起始日期
            end_date:   截止日期
            alpha_num:  因子编号（1~101）
            fill_method: 缺失值填充方式

        Returns:
            pd.DataFrame（行=日期，列=股票代码），或 None（数据为空时）

        Example:
            df = api.compute_alpha(['000001.SZ', '600519.SH'], '2025-01-01', '2026-03-01', 1)
            latest = df.iloc[-1].dropna().sort_values(ascending=False)
        """
        data = self.load_alpha_data(codes, start_date, end_date, fill_method)
        if not data:
            return None
        a = Alpha101(data)
        method_name = f"alpha{alpha_num:03d}"
        method = getattr(a, method_name, None)
        if method is None:
            raise ValueError(f"Alpha101 不存在因子 {method_name}（编号需在 1~101 范围内）")
        return method()

    def compute_alphas(
        self,
        codes: List[str],
        start_date: str,
        end_date: str,
        alphas: Optional[List[int]] = None,
        fill_method: str = "ffill",
    ) -> Dict:
        """
        批量计算多个 Alpha 因子面板。

        Args:
            codes:      股票代码列表
            start_date: 起始日期
            end_date:   截止日期
            alphas:     因子编号列表（如 [1, 5, 12]），None 表示计算全部 101 个
            fill_method: 缺失值填充方式

        Returns:
            Dict[str, pd.DataFrame]，key 为 'alpha001' 等，value 为面板 DataFrame。
            计算出错的因子会被跳过并打印警告，不影响其他因子。

        Example:
            results = api.compute_alphas(
                ['000001.SZ', '600519.SH'],
                '2025-01-01', '2026-03-01',
                alphas=[1, 5, 12, 101],
            )
            for name, df in results.items():
                print(name, df.iloc[-1].describe())
        """
        data = self.load_alpha_data(codes, start_date, end_date, fill_method)
        if not data:
            return {}
        a = Alpha101(data)
        return a.compute_all(alphas=alphas)

    def get_alpha_latest(
        self,
        codes: List[str],
        start_date: str,
        end_date: str,
        alpha_num: int,
        fill_method: str = "ffill",
    ):
        """
        计算单个 Alpha 因子并返回最新一日横截面（已去 NaN，按因子值降序排列）。

        Args:
            codes:      股票代码列表
            start_date: 起始日期（建议给出足够的历史数据，通常 1 年以上）
            end_date:   截止日期（即"最新日"）
            alpha_num:  因子编号（1~101）
            fill_method: 缺失值填充方式

        Returns:
            pd.Series（index=股票代码，values=因子值，降序排列），或 None（数据为空时）

        Example:
            latest = api.get_alpha_latest(
                ['000001.SZ', '600519.SH', '000858.SZ'],
                '2025-01-01', '2026-03-14',
                alpha_num=1,
            )
            print(latest.head(10))   # 因子值最高的 10 只股票
        """
        df = self.compute_alpha(codes, start_date, end_date, alpha_num, fill_method)
        if df is None:
            return None
        return df.iloc[-1].dropna().sort_values(ascending=False)

    def random_alpha_backtest(
        self,
        codes: Optional[List[str]] = None,
        max_screen_factors: int = 5,
        max_signal_factors: int = 7,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        initial_cash: float = 1_000_000.0,
        warmup_days: int = 90,
        random_seed: Optional[int] = None,
        top_n_stocks: int = 5,
    ) -> Dict:
        """
        因子挖矿接口（两阶段：选股 + 交易信号）。

        流程：
          1. 随机抽取 k_screen 个选股因子 + k_signal 个信号因子
          2. 选股阶段：以 start_date 为截面日，每个选股因子随机保留 15%~35% 的股票
          3. 信号阶段：逐日计算信号因子横截面分位排名，综合排名 >= buy_thresh 时买入，
             <= sell_thresh 时卖出（阈值在合理范围内随机生成）
          4. 输出 Top N 个股的每笔交易时的具体因子值与排名

        Args:
            codes:               股票池；None 时取全市场
            max_screen_factors:  选股因子最大数量（默认 3）
            max_signal_factors:  信号因子最大数量（默认 2）
            start_date:          回测起始日，None 取 end_date 前 90 天
            end_date:            回测截止日，None 取今日
            initial_cash:        初始资金（默认 100 万）
            warmup_days:         因子预热天数（默认 90）
            random_seed:         随机种子，None 不固定
            top_n_stocks:        输出详细交易记录的个股数量（默认 5）
        """
        import random
        from datetime import datetime, timedelta
        import pandas as pd
        import numpy as np

        # ── 1. 日期默认值 ──────────────────────────────────────────────────────
        if end_date is None:
            end_date = datetime.today().strftime('%Y-%m-%d')
        if start_date is None:
            start_date = (
                datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=90)
            ).strftime('%Y-%m-%d')

        # ── 2. 股票池 ──────────────────────────────────────────────────────────
        if codes is None:
            codes = self.get_all_symbols()
        if not codes:
            return {'error': '股票池为空'}

        # ── 3. 随机抽取因子（选股 / 信号各自独立不重复，两组间允许重叠）────────
        rng = random.Random(random_seed)
        k_screen = rng.randint(1, max(1, max_screen_factors))
        k_signal = rng.randint(1, max(1, max_signal_factors))
        screen_nums = rng.sample(range(1, 102), k_screen)          # 选股组内不重复
        signal_nums = rng.sample(range(1, 102), k_signal)          # 信号组内不重复

        screen_names = [f'alpha{n:03d}' for n in screen_nums]
        signal_names = [f'alpha{n:03d}' for n in signal_nums]
        # 计算因子时去重（两组可能共享同一因子，只算一次）
        all_nums  = list(dict.fromkeys(screen_nums + signal_nums))  # 保序去重
        all_names = list(dict.fromkeys(screen_names + signal_names))
        all_descs = {name: ALPHA_DESCRIPTIONS.get(name, '') for name in all_names}

        # 选股因子：每个因子随机保留比例 [0.15, 0.35]
        screen_top_pcts = {name: round(rng.uniform(0.15, 0.35), 2) for name in screen_names}

        # 信号因子：综合横截面分位排名阈值
        signal_buy_thresh  = round(rng.uniform(0.55, 0.82), 2)
        signal_sell_thresh = round(rng.uniform(0.10, 0.38), 2)

        # ── 4. 加载面板数据（含预热段）────────────────────────────────────────
        warmup_start = (
            datetime.strptime(start_date, '%Y-%m-%d') - timedelta(days=warmup_days)
        ).strftime('%Y-%m-%d')
        panel = self.load_alpha_data(codes, warmup_start, end_date)
        if not panel:
            return {'error': '无法加载面板数据',
                    'screen_factors': screen_names, 'signal_factors': signal_names}

        close_panel = panel['close']
        start_ts = pd.Timestamp(start_date)
        end_ts   = pd.Timestamp(end_date)
        valid_idx = close_panel.index[close_panel.index <= start_ts]
        ref_date  = valid_idx[-1] if len(valid_idx) > 0 else close_panel.index[0]

        # ── 5. 计算所有因子 ────────────────────────────────────────────────────
        alpha_obj = Alpha101(panel)
        factor_panels: Dict[str, object] = {}
        for num in all_nums:
            name   = f'alpha{num:03d}'
            method = getattr(alpha_obj, name, None)
            if method is None:
                continue
            try:
                factor_panels[name] = method()
            except Exception:
                pass

        # ── 6. 选股阶段：逐因子顺序过滤 ───────────────────────────────────────
        current_pool = set(close_panel.columns.tolist())
        filter_log: List[Dict] = []

        for name in screen_names:
            before   = len(current_pool)
            top_pct  = screen_top_pcts[name]
            if not current_pool or name not in factor_panels:
                filter_log.append({'factor': name, 'status': 'skipped',
                                   'before': before, 'after': before, 'top_pct': top_pct})
                continue
            fp = factor_panels[name]
            if ref_date not in fp.index:
                filter_log.append({'factor': name, 'status': 'no_ref_date',
                                   'before': before, 'after': before, 'top_pct': top_pct})
                continue
            pool_cols = [c for c in current_pool if c in fp.columns]
            snapshot  = fp.loc[ref_date, pool_cols].dropna()
            if snapshot.empty:
                filter_log.append({'factor': name, 'status': 'all_nan',
                                   'before': before, 'after': before, 'top_pct': top_pct})
                continue
            n_keep    = max(1, int(len(snapshot) * top_pct))
            top_codes = set(snapshot.nlargest(n_keep).index)
            current_pool &= top_codes
            filter_log.append({'factor': name, 'status': 'ok',
                               'before': before, 'after': len(current_pool),
                               'ref_date': str(ref_date.date()),
                               'snapshot_size': len(snapshot),
                               'kept': n_keep, 'top_pct': top_pct})

        final_codes = sorted(current_pool)
        if not final_codes:
            return {'screen_k': k_screen, 'signal_k': k_signal,
                    'screen_factors': screen_names, 'signal_factors': signal_names,
                    'factor_descriptions': all_descs,
                    'initial_pool': len(codes), 'filter_log': filter_log,
                    'final_pool': [], 'final_pool_count': 0,
                    'error': '过滤后股票池为空，无法回测'}

        # ── 7. 信号阶段：逐日模拟买卖 ─────────────────────────────────────────
        bt_mask    = (close_panel.index >= start_ts) & (close_panel.index <= end_ts)
        avail_codes = [c for c in final_codes if c in close_panel.columns]
        bt_close   = close_panel.loc[bt_mask, avail_codes]

        if bt_close.empty or len(bt_close) < 2:
            return {'screen_k': k_screen, 'signal_k': k_signal,
                    'screen_factors': screen_names, 'signal_factors': signal_names,
                    'factor_descriptions': all_descs,
                    'initial_pool': len(codes), 'filter_log': filter_log,
                    'final_pool': final_codes, 'final_pool_count': len(final_codes),
                    'error': '回测期内收盘数据不足（< 2 个交易日）'}

        trading_dates = bt_close.index.tolist()

        # 预提取信号因子回测期面板（在筛选后的股票池内计算横截面排名）
        sig_panels: Dict[str, object] = {}
        for name in signal_names:
            if name in factor_panels:
                fp = factor_panels[name]
                sig_cols = [c for c in avail_codes if c in fp.columns]
                if sig_cols:
                    sig_panels[name] = fp.loc[bt_mask, sig_cols]

        fee_rate         = 0.001
        per_stock_budget = initial_cash / len(avail_codes)
        cash             = initial_cash
        positions: Dict[str, Dict] = {}   # code -> {shares, entry_price, entry_date, entry_value}
        equity_curve: List[float]  = [initial_cash]
        trade_log: List[Dict]      = []

        for date in trading_dates:
            date_str = str(date.date())

            # 计算各信号因子当日横截面分位排名
            factor_day_ranks: Dict[str, Dict[str, Dict]] = {}   # name -> code -> {value, rank}
            composite_ranks:  Dict[str, float] = {}

            valid_sig = [n for n in signal_names if n in sig_panels]
            for code in avail_codes:
                per_factor = {}
                rank_vals  = []
                for sname in valid_sig:
                    sp = sig_panels[sname]
                    if code not in sp.columns or date not in sp.index:
                        continue
                    day_series = sp.loc[date].dropna()
                    if day_series.empty or code not in day_series.index:
                        continue
                    raw  = float(day_series[code])
                    rank = float(day_series.rank(pct=True)[code])
                    per_factor[sname] = {'value': round(raw, 6), 'rank': round(rank, 4)}
                    rank_vals.append(rank)
                factor_day_ranks[code] = per_factor
                composite_ranks[code]  = round(float(np.mean(rank_vals)), 4) if rank_vals else 0.5

            # 执行买卖信号
            for code in avail_codes:
                comp = composite_ranks.get(code, 0.5)
                if code not in bt_close.columns:
                    continue
                price_raw = bt_close.loc[date, code]
                if pd.isna(price_raw) or float(price_raw) <= 0:
                    continue
                price = float(price_raw)

                if code not in positions and comp >= signal_buy_thresh:
                    budget = min(per_stock_budget, cash * 0.99)
                    if budget < price * 100:
                        continue
                    shares = int(budget / price / 100) * 100
                    if shares <= 0:
                        continue
                    cost = shares * price * (1 + fee_rate)
                    if cost > cash:
                        continue
                    cash -= cost
                    positions[code] = {'shares': shares, 'entry_price': price,
                                       'entry_date': date_str, 'entry_value': cost}
                    trade_log.append({
                        'date': date_str, 'code': code, 'action': 'BUY',
                        'price': round(price, 3), 'shares': shares, 'amount': round(cost, 2),
                        'composite_rank': comp,
                        'factor_values': factor_day_ranks.get(code, {}),
                        'signal_buy_thresh': signal_buy_thresh,
                        'signal_sell_thresh': signal_sell_thresh,
                    })

                elif code in positions and comp <= signal_sell_thresh:
                    pos      = positions[code]
                    proceeds = pos['shares'] * price * (1 - fee_rate)
                    pnl      = proceeds - pos['entry_value']
                    pnl_pct  = (proceeds / pos['entry_value'] - 1) * 100
                    hold_days = (date - pd.Timestamp(pos['entry_date'])).days
                    cash += proceeds
                    trade_log.append({
                        'date': date_str, 'code': code, 'action': 'SELL',
                        'price': round(price, 3), 'shares': pos['shares'],
                        'amount': round(proceeds, 2),
                        'composite_rank': comp,
                        'factor_values': factor_day_ranks.get(code, {}),
                        'signal_buy_thresh': signal_buy_thresh,
                        'signal_sell_thresh': signal_sell_thresh,
                        'hold_days': hold_days,
                        'pnl': round(pnl, 2),
                        'pnl_pct': round(pnl_pct, 4),
                    })
                    del positions[code]

            # 当日组合净值
            pos_val = sum(
                positions[c]['shares'] * float(bt_close.loc[date, c])
                for c in positions
                if c in bt_close.columns and not pd.isna(bt_close.loc[date, c])
            )
            equity_curve.append(cash + pos_val)

        # 末日强制清仓
        last_date     = trading_dates[-1]
        last_date_str = str(last_date.date())
        for code in list(positions.keys()):
            pos = positions[code]
            if code in bt_close.columns and not pd.isna(bt_close.loc[last_date, code]):
                price    = float(bt_close.loc[last_date, code])
                proceeds = pos['shares'] * price * (1 - fee_rate)
                pnl      = proceeds - pos['entry_value']
                pnl_pct  = (proceeds / pos['entry_value'] - 1) * 100
                hold_days = (last_date - pd.Timestamp(pos['entry_date'])).days
                cash += proceeds
                trade_log.append({
                    'date': last_date_str, 'code': code, 'action': 'SELL(强平)',
                    'price': round(price, 3), 'shares': pos['shares'],
                    'amount': round(proceeds, 2),
                    'composite_rank': None, 'factor_values': {},
                    'signal_buy_thresh': signal_buy_thresh,
                    'signal_sell_thresh': signal_sell_thresh,
                    'hold_days': hold_days,
                    'pnl': round(pnl, 2),
                    'pnl_pct': round(pnl_pct, 4),
                })
        equity_curve[-1] = cash

        # ── 8. 计算业绩指标 ────────────────────────────────────────────────────
        total_ret_dec = (equity_curve[-1] / initial_cash) - 1.0
        trading_days  = len(trading_dates)
        bt_result = {
            'start_date':            start_date,
            'end_date':              end_date,
            'trading_days':          trading_days,
            'initial_cash':          initial_cash,
            'final_value':           round(equity_curve[-1], 2),
            'total_return_pct':      round(total_ret_dec * 100, 4),
            'annualized_return_pct': round(
                self.get_annualized_return(total_ret_dec, trading_days) * 100, 4),
            'max_drawdown_pct':      round(
                self.get_max_drawdown_pct(equity_curve) * 100, 4),
            'sharpe_ratio':          round(self.get_sharpe_ratio(equity_curve), 4),
            'equity_curve':          [round(v, 2) for v in equity_curve],
        }

        # ── 8.5. 基准线对比 ────────────────────────────────────────────────────
        _BENCHMARKS = [
            ('000001.SH', '上证指数'),
            ('000300.SH', '沪深300'),
            ('000905.SH', '中证500'),
            ('399006.SZ', '创业板指'),
        ]
        benchmarks_result: List[Dict] = []

        def _fetch_bench_close(ts_code: str, s_date: str, e_date: str) -> Dict[str, float]:
            """优先查本地 index_daily 表；若表不存在则 fallback 到东方财富爬虫。返回 {YYYY-MM-DD: close}"""
            # ① 尝试本地 DB
            try:
                rows = self.get_index_daily(
                    ts_codes=[ts_code], start_date=s_date, end_date=e_date)
                if rows:
                    return {r.trade_date: r.close for r in rows}
            except Exception:
                pass
            # ② fallback：东方财富历史 K 线接口
            import requests as _req
            code, mkt = ts_code.split('.')
            secid = f"1.{code}" if mkt == 'SH' else f"0.{code}"
            url = 'https://push2his.eastmoney.com/api/qt/stock/kline/get'
            params = {
                'secid': secid,
                'fields1': 'f1,f2,f3,f4,f5,f6',
                'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
                'klt': '101', 'fqt': '0',
                'beg': s_date.replace('-', ''), 'end': e_date.replace('-', ''),
                'lmt': '2000',
            }
            headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://www.eastmoney.com/'}
            resp = _req.get(url, params=params, headers=headers, timeout=10)
            klines = resp.json().get('data', {}).get('klines', [])
            # 字段: 日期,开盘,收盘,最高,最低,成交量,...
            result: Dict[str, float] = {}
            for kl in klines:
                parts = kl.split(',')
                if len(parts) >= 3:
                    result[parts[0]] = float(parts[2])
            return result

        try:
            # 按代码分组：{code: {trade_date: close}}
            bench_map: Dict[str, Dict[str, float]] = {}
            for bcode, _ in _BENCHMARKS:
                try:
                    bench_map[bcode] = _fetch_bench_close(bcode, start_date, end_date)
                except Exception:
                    bench_map[bcode] = {}

            strat_daily_rets = []
            for i in range(1, len(equity_curve)):
                prev = equity_curve[i - 1]
                strat_daily_rets.append((equity_curve[i] / prev - 1.0) if prev else 0.0)

            for bcode, bname in _BENCHMARKS:
                date_close = bench_map.get(bcode, {})
                # 按 trading_dates 对齐，前向填充
                aligned: List[float] = []
                last_val: Optional[float] = None
                for d in trading_dates:
                    v = date_close.get(str(d.date()))
                    if v is not None:
                        last_val = v
                    if last_val is not None:
                        aligned.append(last_val)
                    elif aligned:
                        aligned.append(aligned[-1])
                    # else: 跳过前导无数据日

                if len(aligned) < 2:
                    benchmarks_result.append({
                        'code': bcode, 'name': bname, 'error': '数据不足'})
                    continue

                base0 = aligned[0]
                bench_curve = [initial_cash] + [
                    round(initial_cash * v / base0, 2) for v in aligned]

                b_total_ret_dec = (bench_curve[-1] / initial_cash) - 1.0
                b_td = len(bench_curve) - 1
                b_ann = self.get_annualized_return(b_total_ret_dec, b_td) if b_td > 0 else 0.0
                b_dd  = self.get_max_drawdown_pct(bench_curve)

                # 超额收益率（百分点）
                excess_ret_pct = round(bt_result['total_return_pct'] - b_total_ret_dec * 100, 4)

                # 信息比率：超额日收益序列年化均值/std
                bench_daily_rets = []
                for i in range(1, len(bench_curve)):
                    prev = bench_curve[i - 1]
                    bench_daily_rets.append((bench_curve[i] / prev - 1.0) if prev else 0.0)
                n_common = min(len(strat_daily_rets), len(bench_daily_rets))
                if n_common > 1:
                    excess_daily = [
                        strat_daily_rets[i] - bench_daily_rets[i]
                        for i in range(n_common)]
                    import statistics as _stat
                    mu  = sum(excess_daily) / n_common
                    std = _stat.stdev(excess_daily) if n_common > 1 else 0.0
                    ir  = round((mu / std) * (252 ** 0.5), 4) if std > 1e-10 else 0.0
                else:
                    ir = 0.0

                benchmarks_result.append({
                    'code':                 bcode,
                    'name':                 bname,
                    'total_return_pct':     round(b_total_ret_dec * 100, 4),
                    'annualized_return_pct': round(b_ann * 100, 4),
                    'max_drawdown_pct':     round(b_dd * 100, 4),
                    'excess_return_pct':    excess_ret_pct,
                    'information_ratio':    ir,
                    'equity_curve':         bench_curve,
                })
        except Exception as _e:
            benchmarks_result = [{'error': str(_e)}]

        # ── 8.6. 因子 IC 计算（Rank IC，斯皮尔曼相关系数，纯 numpy 实现）──────
        def _spearman_corr(x: np.ndarray, y: np.ndarray) -> float:
            """计算两个等长数组的斯皮尔曼相关系数。"""
            rx = np.argsort(np.argsort(x)).astype(float)
            ry = np.argsort(np.argsort(y)).astype(float)
            mx, my = rx.mean(), ry.mean()
            num = ((rx - mx) * (ry - my)).sum()
            den = np.sqrt(((rx - mx) ** 2).sum() * ((ry - my) ** 2).sum())
            return float(num / den) if den > 1e-10 else 0.0

        ic_stats: Dict[str, Dict] = {}
        _ic_factors = list(dict.fromkeys(screen_names + signal_names))
        for _fname in _ic_factors:
            if _fname not in factor_panels:
                continue
            _fp = factor_panels[_fname]
            _daily_ic: List[float] = []
            for _i in range(len(trading_dates) - 1):
                _d_cur  = trading_dates[_i]
                _d_next = trading_dates[_i + 1]
                if _d_cur not in _fp.index or _d_next not in bt_close.index:
                    continue
                _factor_day = _fp.loc[_d_cur, avail_codes].dropna()
                _codes_c    = [c for c in _factor_day.index if c in bt_close.columns]
                if len(_codes_c) < 5:
                    continue
                _ret_next  = (bt_close.loc[_d_next, _codes_c] /
                              bt_close.loc[_d_cur,  _codes_c] - 1).dropna()
                _codes_v   = [c for c in _codes_c if c in _ret_next.index]
                if len(_codes_v) < 5:
                    continue
                _rho = _spearman_corr(
                    _factor_day[_codes_v].values,
                    _ret_next[_codes_v].values,
                )
                if not np.isnan(_rho):
                    _daily_ic.append(_rho)

            if len(_daily_ic) < 2:
                ic_stats[_fname] = {'error': '数据不足'}
                continue

            _ic_arr  = np.array(_daily_ic)
            _ic_mean = float(np.mean(_ic_arr))
            _ic_std  = float(np.std(_ic_arr, ddof=1))
            _ic_ir   = round(_ic_mean / _ic_std * (252 ** 0.5), 4) if _ic_std > 1e-10 else 0.0
            ic_stats[_fname] = {
                'ic_mean':     round(_ic_mean, 4),
                'ic_std':      round(_ic_std, 4),
                'ic_ir':       round(_ic_ir, 4),
                'ic_win_rate': round(float(np.mean(_ic_arr > 0)), 4),
                'ic_abs_mean': round(float(np.mean(np.abs(_ic_arr))), 4),
                'ic_series':   [round(v, 4) for v in _daily_ic],
                'n_days':      len(_daily_ic),
            }

        # ── 9. 统计各股表现，取 Top N ──────────────────────────────────────────
        stock_pnl: Dict[str, float] = {}
        for tr in trade_log:
            if tr['action'] in ('SELL', 'SELL(强平)'):
                code = tr['code']
                stock_pnl[code] = stock_pnl.get(code, 0.0) + tr.get('pnl', 0.0)

        top_codes = sorted(stock_pnl, key=lambda c: stock_pnl[c], reverse=True)[:top_n_stocks]
        top_stocks_detail = []
        for code in top_codes:
            code_trades = [tr for tr in trade_log if tr['code'] == code]
            top_stocks_detail.append({
                'code': code,
                'total_pnl': round(stock_pnl[code], 2),
                'trades': code_trades,
            })

        return {
            'screen_k':           k_screen,
            'signal_k':           k_signal,
            'screen_factors':     screen_names,
            'signal_factors':     signal_names,
            'factor_descriptions': all_descs,
            'signal_config': {
                'buy_thresh':  signal_buy_thresh,
                'sell_thresh': signal_sell_thresh,
            },
            'screen_top_pcts':    screen_top_pcts,
            'initial_pool':       len(codes),
            'filter_log':         filter_log,
            'final_pool':         final_codes,
            'final_pool_count':   len(final_codes),
            'trade_log':          trade_log,
            'backtest':           bt_result,
            'benchmarks':         benchmarks_result,
            'ic_stats':           ic_stats,
            'top_stocks':         top_stocks_detail,
        }


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
