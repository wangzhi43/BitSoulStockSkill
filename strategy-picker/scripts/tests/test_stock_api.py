"""
stock_api_test.py — StockApi 类所有接口的编译检查测试

目的：确保所有方法签名无编译错误，不验证业务逻辑。
"""

import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import utils
from track_logger import TrackLogger
from stock_api import StockApi
file_logger = TrackLogger(os.path.join(utils.get_skill_work_dir(), "test.txt"))
api = StockApi(file_logger)

CODE = "000001.SZ"
DATE = "2024-06-03"
START = "2024-01-01"
END   = "2024-06-30"

# ================================================================
# 基础信息
# ================================================================
api.initialSetup()
api.get_all_symbols()
api.get_symbol_basic_infomation(CODE)

# ================================================================
# 实时行情
# ================================================================
api.get_realtime_stock_info(CODE)

# ================================================================
# 财务 / 基本面
# ================================================================
api.query_income(ts_codes=[CODE])
api.query_income(ts_codes=[CODE], report_type="1", end_date="20231231")
api.query_income(ts_codes=[CODE], start_end_date="20230101", limit=5, offset=0, order_by="end_date DESC")

api.get_daily_basic(ts_codes=[CODE])
api.get_daily_basic(trade_date=DATE)
api.get_daily_basic(ts_codes=[CODE], start_date=START, end_date=END, limit=10, offset=0, order_by="trade_date DESC")

api.get_stock_limit(ts_codes=[CODE])
api.get_stock_limit(trade_date=DATE)
api.get_stock_limit(ts_codes=[CODE], start_date=START, end_date=END, limit=5)

api.get_daily_limit_list(trade_date=DATE, limit_type="U")
api.get_daily_limit_list(ts_codes=[CODE])
api.get_daily_limit_list(start_date=START, end_date=END, limit=10)

api.get_daily_bomb_list(trade_date=DATE, bomb_type="U")
api.get_daily_bomb_list(ts_codes=[CODE])
api.get_daily_bomb_list(start_date=START, end_date=END, limit=5)

# ================================================================
# 板块
# ================================================================
api.get_sector_stock_map(sector_codes=["BK0475"])
api.get_sector_stock_map(stock_codes=[CODE])
api.get_sector_stock_map(limit=10, offset=0)

api.get_sector_flow_daily(trade_date=DATE)
api.get_sector_flow_daily(start_date=START, end_date=END, limit=5)

# ================================================================
# 龙虎榜
# ================================================================
api.get_top_list(trade_date=DATE)
api.get_top_list(ts_codes=[CODE])
api.get_top_list(start_date=START, end_date=END, limit=10)

api.get_top_inst(trade_date=DATE)
api.get_top_inst(ts_codes=[CODE])
api.get_top_inst(ts_codes=[CODE], side="0")
api.get_top_inst(ts_codes=[CODE], side="1")
api.get_top_inst(start_date=START, end_date=END, limit=10)
api.get_top_inst(ts_codes=[CODE], start_date=START, end_date=END, limit=5, offset=0, order_by="trade_date DESC")

# ================================================================
# 指数
# ================================================================
api.get_index_basic()
api.get_index_basic(ts_code="000001.SH")
api.get_index_basic(market="SSE", limit=5)

api.get_index_daily(ts_codes=["000001.SH"])
api.get_index_daily(trade_date=DATE)
api.get_index_daily(ts_codes=["000001.SH"], start_date=START, end_date=END, limit=10)

api.get_index_weekly(ts_codes=["000001.SH"])
api.get_index_weekly(start_date=START, end_date=END, limit=5)

api.get_index_monthly(ts_codes=["000001.SH"])
api.get_index_monthly(start_date=START, end_date=END, limit=5)

# ================================================================
# K 线
# ================================================================
api.get_daily_kline([CODE], START, END)
api.get_hour_kline([CODE], START, END)
api.get_weekly_kline([CODE], START, END)
api.get_monthly_kline([CODE], START, END)

# ================================================================
# 价格序列
# ================================================================
api.get_daily_close_prices(CODE, START, END)
api.get_daily_open_prices(CODE, START, END)
api.get_daily_high_prices(CODE, START, END)
api.get_daily_low_prices(CODE, START, END)
api.get_daily_volumes(CODE, START, END)
api.get_daily_pct_chg(CODE, START, END)

# ================================================================
# 技术指标
# ================================================================
api.get_sma(CODE, DATE, period=20)
api.get_ema(CODE, DATE, period=12)
api.get_rsi(CODE, DATE, period=14)
api.get_bollinger_bands(CODE, DATE, period=20, std_dev=2)
api.get_macd(CODE, DATE, fast=12, slow=26, signal=9)
api.get_atr(CODE, DATE, period=14)
api.get_wma(CODE, DATE, period=20)
api.get_tema(CODE, DATE, period=20)
api.get_mom(CODE, DATE, period=10)
api.get_roc(CODE, DATE, period=10)
api.get_cci(CODE, DATE, period=20)
api.get_obv(CODE, DATE, period=20)
api.get_volume(CODE, DATE, period=20)
api.get_kdj(CODE, DATE, n=9, m1=3, m2=3)
api.get_dmi(CODE, DATE, period=14)
api.get_trix(CODE, DATE, period=12)
api.get_sar(CODE, DATE, af_start=0.02, af_max=0.2)
api.get_williams_r(CODE, DATE, period=14)
api.get_psycho(CODE, DATE, period=12)
api.get_bias(CODE, DATE, period=20)
api.get_tr(CODE, DATE)
api.get_natr(CODE, DATE, period=14)
api.get_vwap(CODE, DATE, period=20)
api.get_ad(CODE, DATE, period=20)
api.get_adosc(CODE, DATE, fast=3, slow=10)
api.get_mfi(CODE, DATE, period=14)
api.get_cmo(CODE, DATE, period=14)
api.get_rocp(CODE, DATE, period=10)
api.get_rocr(CODE, DATE, period=10)
api.get_aroon(CODE, DATE, period=14)
api.get_ultosc(CODE, DATE, period1=7, period2=14, period3=28)
api.get_dema(CODE, DATE, period=20)
api.get_kama(CODE, DATE, period=10)
api.get_midpoint(CODE, DATE, period=14)
api.get_midprice(CODE, DATE, period=14)
api.get_pvi(CODE, DATE, period=20)
api.get_nvi(CODE, DATE, period=20)
api.get_ppo(CODE, DATE, fast=12, slow=26, signal=9)
api.get_roc_r(CODE, DATE, period=10)
api.get_stoch(CODE, DATE, fastk_period=14, slowk_period=3, slowd_period=3)
api.get_stochf(CODE, DATE, fastk_period=14, fastd_period=3)
api.get_stochrsi(CODE, DATE, rsi_period=14, stoch_period=14)
api.get_trange(CODE, DATE)
api.get_ma_channel(CODE, DATE, period=20, multiplier=2.0)
api.get_donchian(CODE, DATE, period=20)
api.get_keltner(CODE, DATE, ma_period=20, atr_period=10, multiplier=2.0)
api.get_bbands_width(CODE, DATE, period=20, std_dev=2)
api.get_bbands_pct(CODE, DATE, period=20, std_dev=2)
api.get_linearreg(CODE, DATE, period=14)
api.get_linearreg_angle(CODE, DATE, period=14)
api.get_linearreg_intercept(CODE, DATE, period=14)
api.get_linearreg_slope(CODE, DATE, period=14)
api.get_stddev(CODE, DATE, period=20, nbdev=1)
api.get_tsf(CODE, DATE, period=14)
api.get_var(CODE, DATE, period=20, nbdev=1)
api.get_correl(CODE, DATE, period=20)
api.get_beta(CODE, DATE, period=20)
api.get_ht_dcperiod(CODE, DATE)
api.get_ht_dcphase(CODE, DATE)
api.get_ht_phasor(CODE, DATE)
api.get_ht_sine(CODE, DATE)
api.get_ht_trendmode(CODE, DATE)
api.get_typical_price(CODE, DATE)
api.get_median_price(CODE, DATE)
api.get_weighted_close(CODE, DATE)
api.get_avgp(CODE, DATE)
api.get_asi(CODE, DATE, period=26)
api.get_vr(CODE, DATE, period=26)
api.get_ar(CODE, DATE, period=26)
api.get_br(CODE, DATE, period=26)
api.get_brar(CODE, DATE, period=26)
api.get_dpo(CODE, DATE, period=20)
api.get_bbi(CODE, DATE)
api.get_mass(CODE, DATE, period=25)
api.get_xue_channel(CODE, DATE, period=20)
api.get_consecutive_rise(CODE, DATE)
api.get_consecutive_fall(CODE, DATE)

# ================================================================
# 形态识别
# ================================================================
api.get_bomb_board(CODE, DATE)
api.get_bomb_board_count(CODE, DATE, period=20)
api.get_consecutive_limit_up(CODE, DATE)
api.get_morning_star(CODE, DATE)
api.get_qiming_star(CODE, DATE)
api.get_evening_star(CODE, DATE)
api.get_huanghun_star(CODE, DATE)
api.get_three_white_soldiers(CODE, DATE)
api.get_three_black_crows(CODE, DATE)
api.get_dark_cloud_cover(CODE, DATE)
api.get_rounding_bottom(CODE, DATE, period=60)
api.get_ascending_triangle(CODE, DATE, period=30)
api.get_top_pattern(CODE, DATE, period=60)

# ================================================================
# 股票筛选
# ================================================================
api.get_stocks_by_industry_keyword("银行")
api.get_stocks_by_industry_keyword("半导体", market="主板", limit=10)
api.get_latest_income(CODE)
api.filter_stocks_by_fundamentals(DATE, pe_ttm_max=50.0, roe_min=0.1, mv_min_yi=50.0, top_n=20)
api.scan_all_signals("morning_star", DATE)
api.scan_all_signals("morning_star", DATE, codes=[CODE])

# ================================================================
# 收益率
# ================================================================
api.get_period_return(CODE, START, END)

# ================================================================
# 性能指标
# ================================================================
equity = [1000000.0, 1050000.0, 1020000.0, 1080000.0]
trades = [
    {"profit": 5000.0, "return": 0.05},
    {"profit": -2000.0, "return": -0.02},
]
api.get_max_drawdown(equity)
api.get_max_drawdown_pct(equity)
api.get_annualized_return(0.15, 365)
api.get_total_return(1000000.0, 1150000.0)
api.get_sharpe_ratio(equity, risk_free_rate=0.03)
api.get_win_rate(trades)
api.get_profit_loss_ratio(trades)
api.get_calmar_ratio(equity, 365)
api.get_volatility(equity)
api.get_trade_stats(trades)
api.calculate_metrics(equity, trades, 1000000.0, 365)

# ================================================================
# 交易仿真
# ================================================================
api.simulate_trade("buy", 10.5, 100, fee_rate=0.0003)
api.calculate_trade_cost("sell", 10.5, 100, fee_rate=0.0003, slippage=0.0)
pos = api.create_position(CODE, 100, 10.5, DATE)
api.get_position_value(pos, 11.0)
api.get_position_profit(pos, 11.0)
api.calculate_portfolio_value(500000.0, {CODE: pos}, {CODE: 11.0})
api.get_portfolio_positions({CODE: pos})
api.build_equity_curve([(DATE, 1000000.0), (END, 1050000.0)])
api.calculate_daily_returns(equity)
api.should_buy(10.5, 10.0, 9.5, rsi=40, rsi_oversold=30)
api.should_sell(10.5, 10.0, 11.0, rsi=75, rsi_overbought=70)
api.calculate_drawdown(equity)

# ================================================================
# 委托单
# ================================================================
order = api.create_order(CODE, "buy", 10.5, 100)
api.get_order_status(order)
api.cancel_order(order)

# ================================================================
# 持仓管理
# ================================================================
api.close_position(pos, 11.0, DATE)
api.update_position_price(pos, 11.0)

# ================================================================
# 回测环境
# ================================================================
env = api.init_backtest(initial_cash=1000000.0, fee_rate=0.0003)
api.execute_buy(env, CODE, 10.5, 100, DATE)
api.execute_sell(env, CODE, 11.0, 100)
api.get_equity(env, {CODE: 11.0})
api.record_equity(env, DATE, {CODE: 11.0})

# ================================================================
# 工具
# ================================================================
api.get_price_change_rate(CODE, DATE, days=3)
api.get_top_performers([CODE, "600519.SH"], DATE, days=3, top_n=2)
api.get_price_at_date(CODE, DATE)
api.get_prices_at_dates(CODE, [DATE, END])
api.init_databases()
api.clear_indicator_cache(CODE)
api.clear_indicator_cache()

# ================================================================
# Alpha 因子
# ================================================================
api.load_alpha_data([CODE], START, END)
api.compute_alpha([CODE], START, END, alpha_num=1)
api.compute_alphas([CODE], START, END, alphas=[1, 5, 101])
api.get_alpha_latest([CODE], START, END, alpha_num=1)

# ================================================================
# 获取行情 / 快照
# ================================================================
api.get_tick_data(CODE, DATE)
api.get_realtime_bar(CODE, DATE)

print("===== stock_api_test: 所有接口编译检查通过 =====")
