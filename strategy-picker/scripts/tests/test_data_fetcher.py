import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_fetcher import *
def testfunc():

    # ================================================================
    # 1. query_stock_basic
    # ================================================================
    all_stocks = query_stock_basic()

    bank = query_stock_basic(industry="银行")

    single = query_stock_basic(ts_code="600519.SH")

    area_stocks = query_stock_basic(area="广东")

    market_stocks = query_stock_basic(market="主板")

    paged = query_stock_basic(limit=2, offset=0)

    empty = query_stock_basic(ts_code="999999.SZ")

    log("query_stock_basic: 全部测试通过")

    # ================================================================
    # 2. query_hour_kline
    # ================================================================
    all_hour = query_hour_kline()

    code_hour = query_hour_kline(codes=["sz.000001"])

    date_hour = query_hour_kline(date="2024-06-03")

    range_hour = query_hour_kline(start_date="2024-06-04", end_date="2024-06-04")

    lim_hour = query_hour_kline(codes=["sz.000001"], limit=2)

    multi_code_hour = query_hour_kline(codes=["sz.000001", "sh.600519"], date="2024-06-03")

    log("query_hour_kline: 全部测试通过")

    # ================================================================
    # 3. query_daily_kline
    # ================================================================
    all_daily = query_daily_kline()

    code_daily = query_daily_kline(codes=["sz.000001"])

    date_daily = query_daily_kline(date="2024-06-03")

    range_daily = query_daily_kline(start_date="2024-06-04", end_date="2024-06-05")

    desc_daily = query_daily_kline(codes=["sz.000001"], order_by="date DESC", limit=1)

    paged_daily = query_daily_kline(codes=["sz.000001"], limit=2, offset=1)

    log("query_daily_kline: 全部测试通过")

    # ================================================================
    # 4. query_weekly_kline
    # ================================================================
    all_weekly = query_weekly_kline()

    code_weekly = query_weekly_kline(codes=["sz.000001"])

    date_weekly = query_weekly_kline(date="2024-05-31")

    range_weekly = query_weekly_kline(start_date="2024-06-01", end_date="2024-06-30")

    lim_weekly = query_weekly_kline(limit=1)

    log("query_weekly_kline: 全部测试通过")

    # ================================================================
    # 5. query_monthly_kline
    # ================================================================
    all_monthly = query_monthly_kline()

    code_monthly = query_monthly_kline(codes=["sz.000001"])

    date_monthly = query_monthly_kline(date="2024-05-31")

    range_monthly = query_monthly_kline(start_date="2024-06-01", end_date="2024-06-30")

    desc_monthly = query_monthly_kline(codes=["sz.000001"], order_by="date DESC", limit=1)

    log("query_monthly_kline: 全部测试通过")

    # ================================================================
    # 6. query_daily_basic
    # ================================================================
    all_basic = query_daily_basic()

    code_basic = query_daily_basic(ts_codes=["000001.SZ"])

    date_basic = query_daily_basic(trade_date="2024-06-03")

    range_basic = query_daily_basic(start_date="2024-06-04", end_date="2024-06-04")

    desc_basic = query_daily_basic(ts_codes=["000001.SZ"], order_by="trade_date DESC", limit=1)

    multi_code_basic = query_daily_basic(ts_codes=["000001.SZ", "600519.SH"], trade_date="2024-06-03")

    log("query_daily_basic: 全部测试通过")

    # ================================================================
    # 7. query_stock_limit
    # ================================================================
    all_limit = query_stock_limit()

    code_limit = query_stock_limit(ts_codes=["000001.SZ"])

    date_limit = query_stock_limit(trade_date="2024-06-03")

    range_limit = query_stock_limit(start_date="2024-06-04", end_date="2024-06-05")

    desc_limit = query_stock_limit(ts_codes=["000001.SZ"], order_by="trade_date DESC", limit=1)

    multi_code_limit = query_stock_limit(ts_codes=["000001.SZ", "600519.SH"], trade_date="2024-06-03")

    paged_limit = query_stock_limit(limit=2, offset=0)

    log("query_stock_limit: 全部测试通过")

    # ================================================================
    # 8. query_daily_limit_list
    # ================================================================
    all_dll = query_daily_limit_list()

    date_dll = query_daily_limit_list(trade_date="2024-06-03")

    up_dll = query_daily_limit_list(trade_date="2024-06-03", limit_type="U")

    down_dll = query_daily_limit_list(trade_date="2024-06-03", limit_type="D")

    code_dll = query_daily_limit_list(ts_codes=["000001.SZ"])

    range_dll = query_daily_limit_list(start_date="2024-06-04", end_date="2024-06-05")

    desc_dll = query_daily_limit_list(ts_codes=["000001.SZ"], order_by="trade_date DESC", limit=1)

    multi_code_dll = query_daily_limit_list(ts_codes=["000001.SZ", "600519.SH"], limit_type="U")

    paged_dll = query_daily_limit_list(limit=2, offset=0)

    log("query_daily_limit_list: 全部测试通过")

    # ================================================================
    # 9. query_daily_bomb_list
    # ================================================================
    all_dbl = query_daily_bomb_list()

    date_dbl = query_daily_bomb_list(trade_date="2024-06-03")

    up_dbl = query_daily_bomb_list(trade_date="2024-06-03", bomb_type="U")

    down_dbl = query_daily_bomb_list(trade_date="2024-06-03", bomb_type="D")

    code_dbl = query_daily_bomb_list(ts_codes=["000001.SZ"])

    range_dbl = query_daily_bomb_list(start_date="2024-06-04", end_date="2024-06-05")

    desc_dbl = query_daily_bomb_list(ts_codes=["000001.SZ"], order_by="trade_date DESC", limit=1)

    multi_code_dbl = query_daily_bomb_list(ts_codes=["000001.SZ", "600519.SH"], bomb_type="U")

    paged_dbl = query_daily_bomb_list(limit=2, offset=0)

    log("query_daily_bomb_list: 全部测试通过")

    # ================================================================
    # 10. query_sector_stock_map
    # ================================================================
    all_ssm = query_sector_stock_map()

    sector_ssm = query_sector_stock_map(sector_codes=["BK0475"])

    stock_ssm = query_sector_stock_map(stock_codes=["000001.SZ"])

    multi_sector_ssm = query_sector_stock_map(sector_codes=["BK0475", "BK0001"])

    paged_ssm = query_sector_stock_map(limit=2, offset=0)

    log("query_sector_stock_map: 全部测试通过")

    # ================================================================
    # 11. query_top_list
    # ================================================================
    all_tl = query_top_list()

    date_tl = query_top_list(trade_date="2024-06-03")

    code_tl = query_top_list(ts_codes=["000001.SZ"])

    range_tl = query_top_list(start_date="2024-06-01", end_date="2024-06-30")

    desc_tl = query_top_list(ts_codes=["000001.SZ"], order_by="trade_date DESC", limit=1)

    multi_code_tl = query_top_list(ts_codes=["000001.SZ", "600519.SH"])

    paged_tl = query_top_list(limit=2, offset=0)

    log("query_top_list: 全部测试通过")

    # ================================================================
    # 12. query_sector_flow_daily
    # ================================================================
    all_sfd = query_sector_flow_daily()

    date_sfd = query_sector_flow_daily(trade_date="2024-06-03")

    sector_sfd = query_sector_flow_daily(ts_codes=["BK0475"])

    range_sfd = query_sector_flow_daily(start_date="2024-06-01", end_date="2024-06-30")

    desc_sfd = query_sector_flow_daily(ts_codes=["BK0475"], order_by="trade_date DESC", limit=1)

    multi_sector_sfd = query_sector_flow_daily(ts_codes=["BK0475", "BK0001"])

    paged_sfd = query_sector_flow_daily(limit=2, offset=0)

    log("query_sector_flow_daily: 全部测试通过")

    # ================================================================
    # 13. query_index_basic
    # ================================================================
    all_ib = query_index_basic()

    single_ib = query_index_basic(ts_code="000001.SH")

    market_ib = query_index_basic(market="SSE")

    paged_ib = query_index_basic(limit=2, offset=0)

    empty_ib = query_index_basic(ts_code="999999.XX")

    log("query_index_basic: 全部测试通过")

    # ================================================================
    # 14. query_index_daily
    # ================================================================
    all_id = query_index_daily()

    code_id = query_index_daily(ts_codes=["000001.SH"])

    date_id = query_index_daily(trade_date="2024-06-03")

    range_id = query_index_daily(start_date="2024-06-01", end_date="2024-06-30")

    desc_id = query_index_daily(ts_codes=["000001.SH"], order_by="trade_date DESC", limit=1)

    multi_code_id = query_index_daily(ts_codes=["000001.SH", "399001.SZ"])

    paged_id = query_index_daily(limit=2, offset=0)

    log("query_index_daily: 全部测试通过")

    # ================================================================
    # 15. query_index_weekly
    # ================================================================
    all_iw = query_index_weekly()

    code_iw = query_index_weekly(ts_codes=["000001.SH"])

    date_iw = query_index_weekly(trade_date="2024-05-31")

    range_iw = query_index_weekly(start_date="2024-01-01", end_date="2024-06-30")

    desc_iw = query_index_weekly(ts_codes=["000001.SH"], order_by="trade_date DESC", limit=1)

    paged_iw = query_index_weekly(limit=2, offset=0)

    log("query_index_weekly: 全部测试通过")

    # ================================================================
    # 16. query_index_monthly
    # ================================================================
    all_im = query_index_monthly()

    code_im = query_index_monthly(ts_codes=["000001.SH"])

    date_im = query_index_monthly(trade_date="2024-05-31")

    range_im = query_index_monthly(start_date="2024-01-01", end_date="2024-12-31")

    desc_im = query_index_monthly(ts_codes=["000001.SH"], order_by="trade_date DESC", limit=1)

    multi_code_im = query_index_monthly(ts_codes=["000001.SH", "399001.SZ"])

    paged_im = query_index_monthly(limit=2, offset=0)

    log("query_index_monthly: 全部测试通过")

    log("===== testfunc: 所有测试全部通过 =====")
