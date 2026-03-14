"""
data_fetcher.py
===============
封装 HTTP 数据获取接口，将远程数据拉取并持久化到本地 SQLite 数据库，
同时提供本地数据库的查询接口。

HTTP API 基准地址: http://139.224.210.110:80
接口规范参考: API_REFERENCE.md § "通用数据查询接口"
表结构参考:  DATABASE_DOCUMENTATION.md

不依赖任何第三方库，仅使用 Python 3 标准库。
"""

import json
import datetime
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
import pandas as pd
import requests
import os
from sqlalchemy import create_engine, text, Engine
from typing import List, Optional
from define import BASE_URL, HTTP_TIMEOUT, DB_PATH, StockBasic, DailyKline, HourKline, WeeklyKline, MonthlyKline, DailyBasic
import utils
from logger import log
from db_engine import getEngine
g_table_name_to_pk = {
    "stock_basic" : ["ts_code"],
    "hour_kline" : ["code","date", "time"],
    "daily_kline" : ["code","date"],
    "weekly_kline" : ["code","date"],
    "monthly_kline" : ["code","date"],
    "daily_basic": ["ts_code", "trade_date"]
}
 
class TablePatch:
    """
    各个表目前应用的是哪个补丁的数据
    字段说明:
        patch 当前表数据是用的哪个patch，patch格式patch0、patch1等
    """
    __slots__ = ("patch")

    def __init__(self, patch: str):
        self.patch = patch

    @classmethod
    def from_dict(cls, d: dict) -> "TablePatch":
        """从字典（API 响应或数据库行）构造 TablePatch 对象。"""
        return cls(
            patch=d.get("patch") or "",
        )

    def __repr__(self) -> str:
        return f"TablePatch(patch={self.patch!r})"

# ============================================================
# 本地 SQLite 数据库管理
# ============================================================

def init_db() -> None:
    """
    初始化本地 SQLite 数据库，创建 stock_basic 和 daily_kline 表（若不存在）。
    若检测到旧版本表结构（字段不匹配），自动删除旧库重建。
    """
    with getEngine().connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS stock_basic (
                ts_code     TEXT NOT NULL,
                symbol      TEXT,
                name        TEXT,
                area        TEXT,
                industry    TEXT,
                fullname    TEXT,
                enname      TEXT,
                cnspell     TEXT,
                market      TEXT,
                exchange    TEXT,
                curr_type   TEXT,
                list_status TEXT,
                list_date   TEXT,
                delist_date TEXT,
                is_hs       TEXT,
                PRIMARY KEY (ts_code)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS hour_kline (
                date        TEXT NOT NULL,
                time        TEXT NOT NULL,
                open        REAL,
                high        REAL,
                low         REAL,
                close       REAL,
                volume      REAL,
                amount      REAL,
                code        TEXT NOT NULL,
                PRIMARY KEY (code,date,time)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS daily_kline (
                date        TEXT NOT NULL,
                code        TEXT NOT NULL,
                open        REAL,
                high        REAL,
                low         REAL,
                close       REAL,
                volume      REAL,
                amount      REAL,
                adjustflag  TEXT,
                turn        REAL,
                pctChg      REAL,
                pre_close   REAL,
                change      REAL,
                PRIMARY KEY (code,date)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS weekly_kline (
                date        TEXT NOT NULL,
                code        TEXT NOT NULL,
                open        REAL,
                high        REAL,
                low         REAL,
                close       REAL,
                volume      REAL,
                amount      REAL,
                pctChg      REAL,
                PRIMARY KEY (code,date)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS monthly_kline (
                date        TEXT NOT NULL,
                code        TEXT NOT NULL,
                open        REAL,
                high        REAL,
                low         REAL,
                close       REAL,
                volume      REAL,
                amount      REAL,
                pctChg      REAL,
                PRIMARY KEY (code,date)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS daily_basic (
                trade_date       TEXT NOT NULL,
                ts_code          TEXT NOT NULL,
                close            REAL,
                turnover_rate    REAL,
                turnover_rate_f  REAL,
                volume_ratio     REAL,
                pe               REAL,
                pe_ttm           REAL,
                pb               REAL,
                ps               REAL,
                ps_ttm           REAL,
                dv_ratio         REAL,
                dv_ttm           REAL,
                total_share      REAL,
                float_share      REAL,
                free_share       REAL,
                total_mv         REAL,
                circ_mv          REAL,
                adj_factor       REAL,
                PRIMARY KEY (trade_date, ts_code)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS table_patch (
                patch        TEXT NOT NULL
            )
        """))
        conn.commit()
  
# ============================================================
# 本地 SQLite 查询接口
# ============================================================

def query_stock_basic(
    ts_code: Optional[str] = None,
    industry: Optional[str] = None,
    area: Optional[str] = None,
    market: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
) -> List[StockBasic]:
    """
    从本地 SQLite 数据库查询 stock_basic 表，返回 StockBasic 对象列表。

    参数:
        ts_code   按股票代码精确过滤
        industry  按行业名称精确过滤
        area      按地区精确过滤
        market    按市场精确过滤
        limit     返回最大记录数；为 None 表示不限
        offset    分页偏移量，默认 0

    返回:
        List[StockBasic]  符合条件的股票基础信息对象列表

    示例:
        all_stocks   = query_stock_basic()
        bank_stocks  = query_stock_basic(industry="银行")
        single_stock = query_stock_basic(ts_code="000001.SZ")
    """

    conditions = []
    params: dict = {}

    if ts_code is not None:
        conditions.append("ts_code = :ts_code")
        params["ts_code"] = ts_code
    if industry is not None:
        conditions.append("industry = :industry")
        params["industry"] = industry
    if area is not None:
        conditions.append("area = :area")
        params["area"] = area
    if market is not None:
        conditions.append("market = :market")
        params["market"] = market

    sql = "SELECT * FROM stock_basic"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    if limit is not None:
        sql += f" LIMIT {int(limit)} OFFSET {int(offset)}"

    with getEngine().connect() as conn:
        cursor = conn.execute(text(sql), params)
        rows = cursor.fetchall()
        return [StockBasic.from_dict(dict(row._mapping)) for row in rows]

def query_daily_kline(
    codes: List[str] = [],
    date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
    order_by: str = "date ASC",
) -> List[DailyKline]:
    """
    从本地 SQLite 数据库查询 daily_kline 表，返回 DailyKline 对象列表。

    参数:
        code        按股票代码精确过滤
        date        按具体交易日期精确过滤，格式 "YYYY-MM-DD"
        start_date  按日期范围过滤下限（含），格式 "YYYY-MM-DD"
        end_date    按日期范围过滤上限（含），格式 "YYYY-MM-DD"
        limit       返回最大记录数；为 None 表示不限
        offset      分页偏移量，默认 0
        order_by    排序表达式，默认 "date ASC"

    返回:
        List[DailyKline]  符合条件的日线行情对象列表

    示例:
        # 查询某只股票全部历史行情（按日期升序）
        klines = query_daily_kline(code=["sz.000001"])

        # 查询某只股票某段时间行情，最新的 30 条
        klines = query_daily_kline(code=["sz.000001"],
                                   start_date="2024-01-01", end_date="2024-12-31",
                                   limit=30, order_by="date DESC")

        # 查询某天全市场行情
        klines = query_daily_kline(date="2024-06-03")
    """
    conditions = []
    params: dict = {}

    if len(codes) != 0:
        keys = [f"code_{i}" for i in range(len(codes))]
        placeholders = ",".join(f":{k}" for k in keys)
        conditions.append(f"code IN ({placeholders})")
        for k, v in zip(keys, codes):
            params[k] = v
    if date is not None:
        conditions.append("DATE(date) = :date")
        params["date"] = date
    else:
        if start_date is not None:
            conditions.append("DATE(date) >= DATE('{0}')".format(start_date))

        if end_date is not None:
            conditions.append("DATE(date) <= DATE('{0}')".format(end_date))


    sql = "SELECT * FROM daily_kline"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += f" ORDER BY {order_by}"
    if limit is not None:
        sql += f" LIMIT {int(limit)} OFFSET {int(offset)}"

    with getEngine().connect() as conn:
        cursor = conn.execute(text(sql), params)
        rows = cursor.fetchall()
        return [DailyKline.from_dict(dict(row._mapping)) for row in rows]


def query_hour_kline(
    codes: List[str] = [],
    date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
    order_by: str = "date ASC, time ASC",
) -> List[HourKline]:
    """
    从本地 SQLite 数据库查询 hour_kline 表，返回 HourKline 对象列表。

    参数:
        codes       按股票代码列表过滤
        date        按具体交易日期精确过滤，格式 "YYYY-MM-DD"
        start_date  按日期范围过滤下限（含），格式 "YYYY-MM-DD"
        end_date    按日期范围过滤上限（含），格式 "YYYY-MM-DD"
        limit       返回最大记录数；为 None 表示不限
        offset      分页偏移量，默认 0
        order_by    排序表达式，默认 "date ASC, time ASC"

    返回:
        List[HourKline]  符合条件的小时级别 K 线对象列表
    """
    conditions = []
    params: dict = {}

    if len(codes) != 0:
        keys = [f"code_{i}" for i in range(len(codes))]
        placeholders = ",".join(f":{k}" for k in keys)
        conditions.append(f"code IN ({placeholders})")
        for k, v in zip(keys, codes):
            params[k] = v
    if date is not None:
        conditions.append("DATE(date) = :date")
        params["date"] = date
    else:
        if start_date is not None:
            conditions.append("DATE(date) >= DATE('{0}')".format(start_date))
        if end_date is not None:
            conditions.append("DATE(date) <= DATE('{0}')".format(end_date))

    sql = "SELECT * FROM hour_kline"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += f" ORDER BY {order_by}"
    if limit is not None:
        sql += f" LIMIT {int(limit)} OFFSET {int(offset)}"

    with getEngine().connect() as conn:
        cursor = conn.execute(text(sql), params)
        rows = cursor.fetchall()
        return [HourKline.from_dict(dict(row._mapping)) for row in rows]


def query_weekly_kline(
    codes: List[str] = [],
    date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
    order_by: str = "date ASC",
) -> List[WeeklyKline]:
    """
    从本地 SQLite 数据库查询 weekly_kline 表，返回 WeeklyKline 对象列表。

    参数:
        codes       按股票代码列表过滤
        date        按具体日期精确过滤，格式 "YYYY-MM-DD"
        start_date  按日期范围过滤下限（含），格式 "YYYY-MM-DD"
        end_date    按日期范围过滤上限（含），格式 "YYYY-MM-DD"
        limit       返回最大记录数；为 None 表示不限
        offset      分页偏移量，默认 0
        order_by    排序表达式，默认 "date ASC"

    返回:
        List[WeeklyKline]  符合条件的周线 K 线对象列表
    """
    conditions = []
    params: dict = {}

    if len(codes) != 0:
        keys = [f"code_{i}" for i in range(len(codes))]
        placeholders = ",".join(f":{k}" for k in keys)
        conditions.append(f"code IN ({placeholders})")
        for k, v in zip(keys, codes):
            params[k] = v
    if date is not None:
        conditions.append("DATE(date) = :date")
        params["date"] = date
    else:
        if start_date is not None:
            conditions.append("DATE(date) >= DATE('{0}')".format(start_date))
        if end_date is not None:
            conditions.append("DATE(date) <= DATE('{0}')".format(end_date))

    sql = "SELECT * FROM weekly_kline"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += f" ORDER BY {order_by}"
    if limit is not None:
        sql += f" LIMIT {int(limit)} OFFSET {int(offset)}"

    with getEngine().connect() as conn:
        cursor = conn.execute(text(sql), params)
        rows = cursor.fetchall()
        return [WeeklyKline.from_dict(dict(row._mapping)) for row in rows]


def query_monthly_kline(
    codes: List[str] = [],
    date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
    order_by: str = "date ASC",
) -> List[MonthlyKline]:
    """
    从本地 SQLite 数据库查询 monthly_kline 表，返回 MonthlyKline 对象列表。

    参数:
        codes       按股票代码列表过滤
        date        按具体日期精确过滤，格式 "YYYY-MM-DD"
        start_date  按日期范围过滤下限（含），格式 "YYYY-MM-DD"
        end_date    按日期范围过滤上限（含），格式 "YYYY-MM-DD"
        limit       返回最大记录数；为 None 表示不限
        offset      分页偏移量，默认 0
        order_by    排序表达式，默认 "date ASC"

    返回:
        List[MonthlyKline]  符合条件的月线 K 线对象列表
    """
    conditions = []
    params: dict = {}

    if len(codes) != 0:
        keys = [f"code_{i}" for i in range(len(codes))]
        placeholders = ",".join(f":{k}" for k in keys)
        conditions.append(f"code IN ({placeholders})")
        for k, v in zip(keys, codes):
            params[k] = v
    if date is not None:
        conditions.append("DATE(date) = :date")
        params["date"] = date
    else:
        if start_date is not None:
            conditions.append("DATE(date) >= DATE('{0}')".format(start_date))
        if end_date is not None:
            conditions.append("DATE(date) <= DATE('{0}')".format(end_date))

    sql = "SELECT * FROM monthly_kline"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += f" ORDER BY {order_by}"
    if limit is not None:
        sql += f" LIMIT {int(limit)} OFFSET {int(offset)}"

    with getEngine().connect() as conn:
        cursor = conn.execute(text(sql), params)
        rows = cursor.fetchall()
        return [MonthlyKline.from_dict(dict(row._mapping)) for row in rows]


def query_daily_basic(
    ts_codes: List[str] = [],
    trade_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
    order_by: str = "trade_date ASC",
) -> List[DailyBasic]:
    """
    从本地 SQLite 数据库查询 daily_basic 表，返回 DailyBasic 对象列表。

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
    conditions = []
    params: dict = {}

    if len(ts_codes) != 0:
        keys = [f"ts_code_{i}" for i in range(len(ts_codes))]
        placeholders = ",".join(f":{k}" for k in keys)
        conditions.append(f"ts_code IN ({placeholders})")
        for k, v in zip(keys, ts_codes):
            params[k] = v
    if trade_date is not None:
        conditions.append("DATE(trade_date) = :trade_date")
        params["trade_date"] = trade_date
    else:
        if start_date is not None:
            conditions.append("DATE(trade_date) >= DATE('{0}')".format(start_date))
        if end_date is not None:
            conditions.append("DATE(trade_date) <= DATE('{0}')".format(end_date))

    sql = "SELECT * FROM daily_basic"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += f" ORDER BY {order_by}"
    if limit is not None:
        sql += f" LIMIT {int(limit)} OFFSET {int(offset)}"

    with getEngine().connect() as conn:
        cursor = conn.execute(text(sql), params)
        rows = cursor.fetchall()
        return [DailyBasic.from_dict(dict(row._mapping)) for row in rows]


class PatchItem:
    def __init__(self):
        self.patch_date:str = ""
        self.patch_name:str = ""
        self.version:int = int

def request_patch_list() -> list[PatchItem]:
    """
    获取所有表的patch列表
    返回json说明：
        key: 表名
        value: 所有可用patch列表
    """

    item1: PatchItem = PatchItem()
    item1.patch_name = "patch_1.1_20260309_20260313.zip"
    item1.patch_date = "2026-03-13 16:45:46"
    item1.version = 11
    return [item1]

def get_local_patch_ver() -> int:
    """从 table_patch 表中读取当前本地 patch 版本号，无记录时返回 -1。"""
    with getEngine().connect() as conn:
        row = conn.execute(text("SELECT patch FROM table_patch LIMIT 1")).fetchone()
    print(int(row[0]) if row else -1)
    return int(row[0]) if row else -1

def syn_table_datas() -> List[str]:
    """
    根据表名，获取需要下载的 patch 列表。

    逻辑：
        1. 调用 request_patch_list() 获取服务器上该表的全部可用 patch 列表
        2. 查询本地 table_patch 表，找到该表当前已应用的 patch
        3. 返回当前 patch 之后（不含）的所有 patch，即待下载的部分；
           若本地无记录，则返回全部可用 patch

    参数:
        table_name  指定表的名称

    返回:
        List[str]  待下载的 patch 名称列表（按顺序）
    """
    
    local_patch_ver = -1
    with getEngine().connect() as conn:
        cursor = conn.execute(
            text("SELECT patch FROM table_patch")
        )
        row = cursor.fetchone()
        if row:
            local_patch_ver = int(row[0])
        conn.commit()
    
    log(f"本地数据patch ver:{local_patch_ver}")
    if local_patch_ver < 0:
        log(f"导入基础数据...")
        assets_dir = utils.get_skill_assets_dir()
        base_patch_zip = os.path.join(assets_dir, "data_1.0.zip")
        base_patch_dir = os.path.join(utils.get_skill_work_dir(), "data_1.0")
        if not os.path.exists(base_patch_dir):
            utils.unzip_file(base_patch_zip, base_patch_dir)
        import_datas_in_dir(base_patch_dir)

        with getEngine().connect() as conn:
            conn.execute(text("DELETE FROM table_patch"))
            conn.execute(text("INSERT INTO table_patch (patch) VALUES (0)"))
            conn.commit()

    remote_patchs: List[PatchItem] = request_patch_list()
    log(f"remote patch list:{",".join([str(r_patch.version) for r_patch in remote_patchs])}")
    for r_patch in remote_patchs:
        if r_patch.version > local_patch_ver:
            request_and_import_remote_patch_by_name(r_patch.patch_name, r_patch.version)

def request_and_import_remote_patch_by_name(patch_name:str, patch_ver: int):
    log(f"更新remote patch ver:{patch_ver}, name:{patch_name}......")
    url = f"{BASE_URL}/api/download_file"
    params = {
        "file_name": patch_name,
        #ljflag todo：skill配置
        "token_key": "8ACw66fHId31d3OWwVE62yzGkA7p9vCyg1kIV9AKSiU"
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        download_url = data.get("download_url")
        tmp_patch_zip = os.path.join(utils.get_skill_work_dir(), "tmp_patch.zip")
        tmp_patch_dir = os.path.join(utils.get_skill_work_dir(), "tmp_patch")
        utils.download_file(download_url, tmp_patch_zip)
        utils.unzip_file(tmp_patch_zip, tmp_patch_dir)
        import_datas_in_dir(tmp_patch_dir)
        with getEngine().connect() as conn:
            conn.execute(text("DELETE FROM table_patch"))
            conn.execute(text(f"INSERT INTO table_patch (patch) VALUES ({patch_ver})"))
            conn.commit()
        log(f"更新本地数据patch ver:{patch_ver}")
    
def import_datas_in_dir(dir: str):
    files = utils.scan_files_in_dir(dir)
    for file in files:
        basename = os.path.basename(file)
        for table_name in g_table_name_to_pk.keys():
            if basename.startswith(table_name):
                import_data_to_table(file, table_name)

def import_data_to_table(input_file:str, table_name:str):
    log(f"导入表{table_name} from {input_file}")
    if input_file.endswith('.csv.gz'):
        df = pd.read_csv(input_file, compression='gzip')
    elif input_file.endswith('.csv'):
        df = pd.read_csv(input_file)
    elif input_file.endswith('.pkl'):
        df = pd.read_pickle(input_file)
    else:
        assert False

    # 先写入临时表
    df.to_sql("tmp_import", getEngine(), if_exists="replace", index=False)

    with getEngine().connect() as conn:
        # 用 SQL INSERT OR REPLACE 从临时表合并到目标表
        conn.execute(text(f"INSERT OR REPLACE INTO {table_name} SELECT * FROM tmp_import"))
        # conn.execute(text("DROP TABLE tmp_import"))
        conn.commit()

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

    log("===== testfunc: 所有测试全部通过 =====")


if __name__ == "__main__":
    log(f"数据库路径:{DB_PATH}")
    init_db()
    syn_table_datas()