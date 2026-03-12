"""
stock_api.py — 股票数据与回测API接口

策略逻辑可调用此模块中的所有函数来获取股票数据。
当前为模拟实现，真实环境中替换为实际数据源即可。
策略逻辑可调用此模块中的所有函数来获取股票数据和技术指标。
本模块是项目对外的唯一接口，其他模块的实现在内部4个独立文件中。

使用示例:
    from stock_api import StockApi
    
    api = StockApi()
    
    # 获取K线数据
    klines = api.get_kline(['600519.SH'], '2026-01-01', '2026-03-01')
    
    # 获取技术指标
    sma = api.get_sma('600519.SH', '2026-03-01', 20)
    rsi = api.get_rsi('600519.SH', '2026-03-01', 14)
    
    # 获取性能指标
    report = api.calculate_metrics([1000000, 1050000, 1020000], trades, 1000000, 30)
"""

import sys
from typing import Optional, List, Dict

sys.path.insert(0, __file__.rsplit('/', 1)[0])

from data_fetcher import query_stock_basic, query_daily_kline
from define import DailyKline, StockBasic

from data_loader import (
    get_kline as _get_kline,
    get_close_prices,
    get_dates,
    get_open_prices,
    get_high_prices,
    get_low_prices,
    get_volumes,
    get_pct_chg,
    get_stock_info,
    get_all_stocks,
    get_stock_codes,
)

from indicators import (
    get_sma,
    get_ema,
    get_rsi,
    get_bollinger_bands,
    get_macd,
    get_atr,
    init_indicators_db,
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

    def __init__(self):
        """初始化StockApi，建议在使用指标前调用"""
        init_indicators_db()

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

    def get_close_prices(self, code: str, start_date: str, end_date: str) -> List[float]:
        """
        获取指定股票的收盘价列表（按日期升序）。
        
        Args:
            code: 股票代码
            start_date: 起始日期
            end_date: 结束日期
        
        Returns:
            收盘价列表
        
        Example:
            prices = api.get_close_prices('600519.SH', '2026-01-01', '2026-03-01')
        """
        return get_close_prices(code, start_date, end_date)

    def get_dates(self, code: str, start_date: str, end_date: str) -> List[str]:
        """
        获取指定股票的日期列表（按日期升序）。
        
        Args:
            code: 股票代码
            start_date: 起始日期
            end_date: 结束日期
        
        Returns:
            日期列表，格式 YYYY-MM-DD
        
        Example:
            dates = api.get_dates('600519.SH', '2026-01-01', '2026-03-01')
        """
        return get_dates(code, start_date, end_date)

    def get_open_prices(self, code: str, start_date: str, end_date: str) -> List[float]:
        """
        获取指定股票的开盘价列表。
        
        Args:
            code: 股票代码
            start_date: 起始日期
            end_date: 结束日期
        
        Returns:
            开盘价列表
        """
        return get_open_prices(code, start_date, end_date)

    def get_high_prices(self, code: str, start_date: str, end_date: str) -> List[float]:
        """
        获取指定股票的最高价列表。
        
        Args:
            code: 股票代码
            start_date: 起始日期
            end_date: 结束日期
        
        Returns:
            最高价列表
        """
        return get_high_prices(code, start_date, end_date)

    def get_low_prices(self, code: str, start_date: str, end_date: str) -> List[float]:
        """
        获取指定股票的最低价列表。
        
        Args:
            code: 股票代码
            start_date: 起始日期
            end_date: 结束日期
        
        Returns:
            最低价列表
        """
        return get_low_prices(code, start_date, end_date)

    def get_volumes(self, code: str, start_date: str, end_date: str) -> List[float]:
        """
        获取指定股票的成交量列表。
        
        Args:
            code: 股票代码
            start_date: 起始日期
            end_date: 结束日期
        
        Returns:
            成交量列表
        """
        return get_volumes(code, start_date, end_date)

    def get_pct_chg(self, code: str, start_date: str, end_date: str) -> List[float]:
        """
        获取指定股票的涨跌幅列表。
        
        Args:
            code: 股票代码
            start_date: 起始日期
            end_date: 结束日期
        
        Returns:
            涨跌幅列表(%)
        """
        return get_pct_chg(code, start_date, end_date)

    # ============================================================
    # 技术指标类接口（带缓存）
    # ============================================================

    def get_sma(self, code: str, date: str, period: int = 20) -> Optional[float]:
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
        return get_sma(code, date, period)

    def get_ema(self, code: str, date: str, period: int = 12) -> Optional[float]:
        """
        获取指数移动平均EMA。
        
        Args:
            code: 股票代码
            date: 计算日期
            period: 周期，默认12
        
        Returns:
            EMA值，若数据不足返回None
        """
        return get_ema(code, date, period)

    def get_rsi(self, code: str, date: str, period: int = 14) -> Optional[float]:
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
        return get_rsi(code, date, period)

    def get_bollinger_bands(self, code: str, date: str, period: int = 20, std_dev: int = 2) -> Optional[Dict[str, float]]:
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
        return get_bollinger_bands(code, date, period, std_dev)

    def get_macd(self, code: str, date: str, fast: int = 12, slow: int = 26, signal: int = 9) -> Optional[Dict[str, float]]:
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
        return get_macd(code, date, fast, slow, signal)

    def get_atr(self, code: str, date: str, period: int = 14) -> Optional[float]:
        """
        获取平均真实波幅ATR。
        
        Args:
            code: 股票代码
            date: 计算日期
            period: 周期，默认14
        
        Returns:
            ATR值，若数据不足返回None
        """
        return get_atr(code, date, period)

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

    # ============================================================
    # 持仓管理接口（增强版）
    # ============================================================

    def open_position(self, code: str, price: float, quantity: int, date: str) -> Position:
        """
        开仓（买入股票建立多头持仓）。
        
        Args:
            code: 股票代码
            price: 开仓价格
            quantity: 数量（股，必须是100的倍数）
            date: 开仓日期
        
        Returns:
            Position对象
        
        Example:
            pos = api.open_position('600519.SH', 1800.0, 100, '2026-01-01')
        """
        return create_position(code, quantity, price, date)

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

    def buy(self, cash: float, positions: Dict[str, Position], code: str, price: float, quantity: int, date: str, fee_rate: float = 0.0003) -> Tuple[float, Dict[str, Position], TradeResult]:
        """
        买入股票（纯函数，无副作用）。
        
        Args:
            cash: 当前现金
            positions: 持仓字典 {code: Position}
            code: 股票代码
            price: 买入价格
            quantity: 买入数量
            date: 交易日期
            fee_rate: 手续费率，默认0.0003
        
        Returns:
            (更新后的现金, 更新后的持仓字典, 交易结果TradeResult)
        
        Example:
            new_cash, new_positions, result = api.buy(1000000, {}, '600519.SH', 1800.0, 100, '2026-01-01')
            if result.success:
                print(f买入成功，成本: {result.cost})
        """
        return buy(cash, positions, code, price, quantity, date, fee_rate)

    def sell(self, cash: float, positions: Dict[str, Position], code: str, price: float, quantity: int, fee_rate: float = 0.0003) -> Tuple[float, Dict[str, Position], TradeResult]:
        """
        卖出股票（纯函数，无副作用）。
        
        Args:
            cash: 当前现金
            positions: 持仓字典 {code: Position}
            code: 股票代码
            price: 卖出价格
            quantity: 卖出数量
            fee_rate: 手续费率，默认0.0003
        
        Returns:
            (更新后的现金, 更新后的持仓字典, 交易结果TradeResult)
        
        Example:
            new_cash, new_positions, result = api.sell(900000, positions, '600519.SH', 1900.0, 100)
            if result.success:
                print(f"卖出成功，净收款: {result.net_proceeds}")
        """
        return sell(cash, positions, code, price, quantity, fee_rate)

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
