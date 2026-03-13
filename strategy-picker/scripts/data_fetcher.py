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
import os
from sqlalchemy import create_engine, text
from typing import List, Optional
from define import BASE_URL, HTTP_TIMEOUT, DB_PATH, StockBasic, DailyKline
import utils
g_table_name_to_pk = {
    # "stock_basic" : "ts_code",
    # "hour_kline" : "code",
    # "daily_kline" : "code",
    # "weekly_kline" : "code",
    "monthly_kline" : "code",
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
# 内部 HTTP 工具
# ============================================================

def _http_get(table_name: str, params: dict) -> dict:
    """
    向远程 API 发送一次 GET 请求并返回 JSON 响应体（dict）。

    URL 格式: GET /api/<table_name>?param1=v1&param2=v2
    出错时抛出 RuntimeError，包含 HTTP 状态码或网络错误信息。
    """
    url = f"{BASE_URL}/api/{table_name}"
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"

    try:
        with urllib.request.urlopen(url, timeout=HTTP_TIMEOUT) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} 请求 {url} 失败: {e.reason}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"网络请求失败 {url}: {e.reason}") from e


def _fetch_page(table_name: str, filters: dict,
                limit: int = 100, offset: int = 0) -> List[dict]:
    """
    拉取 table_name 表中满足 filters 条件的一页记录。

    参数:
        table_name  远程表名
        filters     过滤条件字典，直接作为 URL 查询参数传递
        limit       本次请求返回的最大记录数，默认 100
        offset      分页偏移量，默认 0
    返回原始字典列表。
    """
    params = dict(filters)
    params["limit"] = limit
    params["offset"] = offset

    resp = _http_get(table_name, params)
    return resp.get("data", [])


# ============================================================
# 远程 HTTP 数据拉取接口
# ============================================================

def fetch_stock_basic() -> List[StockBasic]:
    """
    从远程 API 拉取 stock_basic（股票基础信息）数据，返回 StockBasic 对象列表。

    参数:
        无

    返回:
        List[StockBasic]  股票基础信息对象列表
    """
     
    url = f"{BASE_URL}/api/stock_basic/all"
    with urllib.request.urlopen(url, timeout=HTTP_TIMEOUT) as resp:
        raw = resp.read().decode("utf-8")
        raw_json = json.loads(raw)
    return [StockBasic.from_dict(row) for row in raw_json.get("data", [])]


def fetch_daily_kline(
    start_date: str,
    end_date: str
) -> List[DailyKline]:
    """
    从远程 API 拉取指定日期范围内的daily_kline（日线行情）数据，返回 DailyKline 对象列表。

    参数:
        start_date 必选，起始日期，yyyy-mm-dd格式
        end_date 必选，结束日期，yyyy-mm-dd格式

    返回:
        List[DailyKline]  日线行情对象列表
    """
     
    url = f"{BASE_URL}/api/export/daily_kline?{urllib.parse.urlencode({'start_date': start_date, 'end_date': end_date})}"
    with urllib.request.urlopen(url, timeout=HTTP_TIMEOUT) as resp:
        raw = resp.read().decode("utf-8")
        raw_json = json.loads(raw)

    return [DailyKline.from_dict(row) for row in raw_json.get("data", [])]


# ============================================================
# 本地 SQLite 数据库管理
# ============================================================

def _get_conn() -> sqlite3.Connection:
    """
    打开（或创建）指定路径的 SQLite 数据库并返回连接对象。
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row   # 使列可按名称访问
    return conn


def _db_schema_is_outdated() -> bool:
    """检查 stock_basic 表是否使用旧字段（code 而非 ts_code）。"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.execute("PRAGMA table_info(stock_basic)")
        cols = {row[1] for row in cursor.fetchall()}
        conn.close()
        return bool(cols) and "ts_code" not in cols
    except Exception:
        return False


def init_db() -> None:
    """
    初始化本地 SQLite 数据库，创建 stock_basic 和 daily_kline 表（若不存在）。
    若检测到旧版本表结构（字段不匹配），自动删除旧库重建。
    """
    # 若旧库字段已过期，删除后重建
    if os.path.exists(DB_PATH) and _db_schema_is_outdated():
        os.remove(DB_PATH)
        for ext in ("-wal", "-shm"):
            p = DB_PATH + ext
            if os.path.exists(p):
                os.remove(p)
    conn = _get_conn()
    try:
        conn.executescript("""
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
                list_date   TEXT,
                delist_date TEXT,
                is_hs       TEXT,
                PRIMARY KEY (ts_code)
            );
                           
            CREATE TABLE IF NOT EXISTS hour_kline (
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
                PRIMARY KEY (code)
            );
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
                PRIMARY KEY (code)
            );
                           
            CREATE TABLE IF NOT EXISTS weekly_kline (
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
                PRIMARY KEY (code)
            );
                           
            CREATE TABLE IF NOT EXISTS monthly_kline (
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
                PRIMARY KEY (code)
            );
                           
            CREATE TABLE IF NOT EXISTS table_patch (
                patch        TEXT NOT NULL
            );
 
        """)
        conn.commit()
    finally:
        conn.close()


# ============================================================
# 数据写入接口（HTTP → SQLite）
# ============================================================

def save_stock_basic(records: List[StockBasic]) -> int:
    """
    将 StockBasic 对象列表批量写入本地 SQLite stock_basic 表。
    使用 INSERT OR REPLACE 保证重复执行时幂等（按主键 code 覆盖旧数据）。

    参数:
        records  StockBasic 对象列表

    返回:
        int  实际写入（插入或替换）的记录数

    示例:
        items = fetch_stock_basic()
        count = save_stock_basic(items, "/tmp/stock_data.db")
    """
    if not records:
        return 0

    conn = _get_conn()
    try:
        rows = [
            (r.ts_code, r.symbol, r.name, r.area, r.industry,
             r.fullname, r.enname, r.cnspell, r.market, r.exchange,
             r.curr_type, r.list_date, r.delist_date, r.is_hs)
            for r in records
        ]
        conn.executemany(
            """INSERT OR REPLACE INTO stock_basic
               (ts_code, symbol, name, area, industry, fullname, enname,
                cnspell, market, exchange, curr_type, list_date, delist_date, is_hs)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )
        conn.commit()
        return len(rows)
    finally:
        conn.close()


def save_daily_kline(records: List[DailyKline]) -> int:
    """
    将 DailyKline 对象列表批量写入本地 SQLite daily_kline 表。
    使用 INSERT OR REPLACE 保证重复执行时幂等（按主键 (date, code) 覆盖旧数据）。

    参数:
        records  DailyKline 对象列表

    返回:
        int  实际写入（插入或替换）的记录数

    示例:
        klines = fetch_daily_kline(code="sz.000001")
        count  = save_daily_kline(klines, "/tmp/stock_data.db")
    """
    if not records:
        return 0

    conn = _get_conn()
    try:
        rows = [
            (r.date, r.code, r.open, r.high, r.low, r.close,
             r.volume, r.amount, r.adjustflag, r.turn, r.pctChg,
             r.pre_close, r.change)
            for r in records
        ]
        conn.executemany(
            """INSERT OR REPLACE INTO daily_kline
               (date, code, open, high, low, close, volume, amount,
                adjustflag, turn, pctChg, pre_close, change)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )
        conn.commit()
        return len(rows)
    finally:
        conn.close()


# ============================================================
# 一键同步接口（fetch + save 组合）
# ============================================================

def sync_all_stock_basic() -> int:
    """
    从远程 API 拉取 stock_basic 数据并同步到本地 SQLite。
    若数据库或表不存在则自动初始化。

    参数:
        无

    返回:
        int  写入记录数
    """
    init_db()
    conn = _get_conn()
    try:
        row = conn.execute("SELECT COUNT(*) FROM stock_basic").fetchone()
        count = row[0] if row else 0
    finally:
        conn.close()
    if count > 0:
        print(f"同步股票基础信息:已有 {count} 条数据，跳过同步")
        return 0
    records = fetch_stock_basic()
    syn_count = save_stock_basic(records)
    print(f"同步股票基础信息:已同步{syn_count}条数据")
    return syn_count

def sync_recent_daily_kline(days: int = 30) -> int:
    """
    同步最近 N 天的日线行情数据到本地数据库。

    若数据库中已有数据且最新日期在 10 天以内，则从该日期起增量拉取；
    否则从今天往前推 days 天全量拉取。

    参数:
        days  往前追溯的天数，默认 30

    返回:
        int  写入记录数

    示例:
        # 同步最近30天数据，若本地数据较新则自动增量
        sync_recent_daily_kline(30)
    """
    
    init_db()

    today = datetime.date.today()
    today_str = today.strftime("%Y-%m-%d")

    # 查询本地最新日期
    fetch_from = None
    try:
        conn = _get_conn()
        cursor = conn.execute("SELECT MAX(date) FROM daily_kline")
        row = cursor.fetchone()
        conn.close()
        latest_str = row[0] if row and row[0] else None
        if latest_str:
            latest_date = datetime.date.fromisoformat(latest_str)
            gap_days = (today - latest_date).days
            if gap_days <= 10:
                fetch_from = latest_str
    except Exception:
        pass

    if fetch_from is None:
        start_str = (today - datetime.timedelta(days=days)).strftime("%Y-%m-%d")
    else:
        start_str = fetch_from

    records = fetch_daily_kline(start_date=start_str, end_date=today_str)
    syn_count = save_daily_kline(records)
    print(f"同步股票日线行情: 已同步 {syn_count} 条（{start_str} ~ {today_str}）")
    return syn_count


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
    params: list = []

    if ts_code is not None:
        conditions.append("ts_code = ?")
        params.append(ts_code)
    if industry is not None:
        conditions.append("industry = ?")
        params.append(industry)
    if area is not None:
        conditions.append("area = ?")
        params.append(area)
    if market is not None:
        conditions.append("market = ?")
        params.append(market)

    sql = "SELECT * FROM stock_basic"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    if limit is not None:
        sql += f" LIMIT {int(limit)} OFFSET {int(offset)}"

    conn = _get_conn()
    try:
        cursor = conn.execute(sql, params)
        rows = cursor.fetchall()
        # print("[query_stock_basic] sql:",sql, "params:",params)
        return [StockBasic.from_dict(dict(row)) for row in rows]
    finally:
        conn.close()


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
    params: list = []

    if len(codes) != 0:
        placeholders = ",".join("?" * len(codes))
        conditions.append(f"code IN ({placeholders})")
        params.extend(codes)
    if date is not None:
        conditions.append("DATE(date) = ?")
        params.append(date)
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

    conn = _get_conn()
    try:
        cursor = conn.execute(sql, params)
        rows = cursor.fetchall()
        # print("[query_daily_kline] sql:",sql, "params:",params, "rows:", len(rows))
        return [DailyKline.from_dict(dict(row)) for row in rows]
    finally:
        conn.close()

 
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
    remote_patchs: List[PatchItem] = request_patch_list()
    local_patch_ver = -1
 
    conn = _get_conn()
    cursor = conn.execute(
        "SELECT patch FROM table_patch"
    )
    row = cursor.fetchone()
    conn.commit()
    if row:
        local_patch_ver = int(row[0])
    print(f"local_patch_ver:{local_patch_ver}")
    if local_patch_ver >= 0:
        print("查询")
    else:
        assets_dir = utils.get_skill_assets_dir()
        patch0 = os.path.join(assets_dir, "patch0")
        import_datas_in_dir(patch0)
        conn.execute(f"INSERT OR REPLACE INTO table_patch (patch) VALUES ({'0'})")
        conn.commit()
    need_update_patchs = []
    for r_patch in remote_patchs:
        if r_patch.version > local_patch_ver:
            need_update_patchs.append(r_patch)
            print(r_patch.version)
    conn.close()

def import_datas_in_dir(dir: str):
    files = utils.scan_files_in_dir(dir)
    for file in files:
        basename = os.path.basename(file)
        for table_name in g_table_name_to_pk.keys():
            if basename.startswith(table_name):
                import_data_to_table(file, table_name)

def import_data_to_table(input_file:str, table_name:str):
    print(table_name, input_file)
    if input_file.endswith('.csv.gz'):
        df = pd.read_csv(input_file, compression='gzip')
    elif input_file.endswith('.csv'):
        df = pd.read_csv(input_file)
    elif input_file.endswith('.pkl'):
        df = pd.read_pickle(input_file)
    else:
        assert False
    engine = create_engine(f"sqlite:///{DB_PATH}")

    # 先写入临时表
    df.to_sql("tmp_import", engine, if_exists="replace", index=False)

    with engine.connect() as conn:
        # 目标表不存在时，按临时表结构创建，并设置主键
        col_defs = ", ".join(
            f"{col} TEXT PRIMARY KEY" if col == g_table_name_to_pk[table_name] else f"{col} TEXT"
            for col in df.columns
        )
        conn.execute(text(f"CREATE TABLE IF NOT EXISTS {table_name} ({col_defs})"))
        # 用 SQL INSERT OR REPLACE 从临时表合并到目标表
        conn.execute(text(f"INSERT OR REPLACE INTO {table_name} SELECT * FROM tmp_import"))
        conn.execute(text("DROP TABLE tmp_import"))
        conn.commit()

if __name__ == "__main__":
    print("数据库路径:",DB_PATH)
    init_db()
    syn_table_datas()
    # import_data_to_table(input_file="/Users/liujie/Desktop/claw/stock_basic50.csv", 
    #                      table_name="test", 
    #                      pk=g_table_name_to_pk["test"])
    # sync_all_stock_basic()
    # sync_recent_daily_kline(10)