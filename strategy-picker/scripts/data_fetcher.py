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
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
from typing import List, Optional
from define import BASE_URL, HTTP_TIMEOUT, DB_PATH, StockBasic, DailyKline

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

def fetch_stock_basic(
    code: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[StockBasic]:
    """
    从远程 API 拉取 stock_basic（股票基础信息）数据，返回 StockBasic 对象列表。

    参数:
        code    按股票代码精确过滤，如 "sz.000001"；为 None 时拉取全部
        status  按上市状态过滤，"1" 表示上市，"0" 表示退市；为 None 时不过滤
        limit   单次请求返回的最大记录数，默认 100
        offset  分页偏移量，默认 0

    返回:
        List[StockBasic]  股票基础信息对象列表

    示例:
        records = fetch_stock_basic()                          # 全量
        record  = fetch_stock_basic(code="sz.000001")          # 单只
        listed  = fetch_stock_basic(status="1")                # 仅上市股票
        page2   = fetch_stock_basic(limit=100, offset=100)     # 第二页
    """
    filters: dict = {}
    if code is not None:
        filters["code"] = code
    if status is not None:
        filters["status"] = status

    raw_rows = _fetch_page("stock_basic", filters, limit=limit, offset=offset)
    return [StockBasic.from_dict(row) for row in raw_rows]


def fetch_daily_kline(
    code: Optional[str] = None,
    date: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[DailyKline]:
    """
    从远程 API 拉取 daily_kline（日线行情）数据，返回 DailyKline 对象列表。

    参数:
        code    按股票代码精确过滤，如 "sz.000001"；为 None 时不限
        date    按具体交易日期精确过滤，格式 "YYYY-MM-DD"；为 None 时不限
        limit   单次请求返回的最大记录数，默认 100
        offset  分页偏移量，默认 0

    返回:
        List[DailyKline]  日线行情对象列表

    示例:
        # 拉取某只股票全部历史行情
        klines = fetch_daily_kline(code="sz.000001")

        # 拉取某天全市场行情
        klines = fetch_daily_kline(date="2024-01-02")

        # 分页拉取
        klines = fetch_daily_kline(code="sz.000001", limit=50, offset=100)
    """
    filters: dict = {}
    if code is not None:
        filters["code"] = code
    if date is not None:
        filters["date"] = date

    raw_rows = _fetch_page("daily_kline", filters, limit=limit, offset=offset)
    return [DailyKline.from_dict(row) for row in raw_rows]


# ============================================================
# 本地 SQLite 数据库管理
# ============================================================

def _get_conn(db_path: str) -> sqlite3.Connection:
    """
    打开（或创建）指定路径的 SQLite 数据库并返回连接对象。
    同时启用 WAL 模式以提升并发读写性能。
    """
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row   # 使列可按名称访问
    return conn


def init_db(db_path: str) -> None:
    """
    初始化本地 SQLite 数据库，创建 stock_basic 和 daily_kline 表（若不存在）。

    参数:
        db_path  数据库文件路径，如 "./data/stock.db" 或绝对路径

    示例:
        init_db("/tmp/stock_data.db")
    """
    conn = _get_conn(db_path)
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS stock_basic (
                code        TEXT PRIMARY KEY,
                code_name   TEXT,
                pinyin      TEXT,
                ipoDate     TEXT,
                outDate     TEXT,
                type        TEXT,
                status      TEXT,
                industry    TEXT,
                area        TEXT,
                market      TEXT
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
                PRIMARY KEY (date, code)
            );

            CREATE INDEX IF NOT EXISTS idx_daily_kline_code ON daily_kline(code);
            CREATE INDEX IF NOT EXISTS idx_daily_kline_date ON daily_kline(date);
        """)
        conn.commit()
    finally:
        conn.close()


# ============================================================
# 数据写入接口（HTTP → SQLite）
# ============================================================

def save_stock_basic(records: List[StockBasic], db_path: str) -> int:
    """
    将 StockBasic 对象列表批量写入本地 SQLite stock_basic 表。
    使用 INSERT OR REPLACE 保证重复执行时幂等（按主键 code 覆盖旧数据）。

    参数:
        records  StockBasic 对象列表
        db_path  目标数据库文件路径

    返回:
        int  实际写入（插入或替换）的记录数

    示例:
        items = fetch_stock_basic()
        count = save_stock_basic(items, "/tmp/stock_data.db")
    """
    if not records:
        return 0

    conn = _get_conn(db_path)
    try:
        rows = [
            (r.code, r.code_name, r.pinyin, r.ipoDate, r.outDate,
             r.type, r.status, r.industry, r.area, r.market)
            for r in records
        ]
        conn.executemany(
            """INSERT OR REPLACE INTO stock_basic
               (code, code_name, pinyin, ipoDate, outDate, type, status, industry, area, market)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )
        conn.commit()
        return len(rows)
    finally:
        conn.close()


def save_daily_kline(records: List[DailyKline], db_path: str) -> int:
    """
    将 DailyKline 对象列表批量写入本地 SQLite daily_kline 表。
    使用 INSERT OR REPLACE 保证重复执行时幂等（按主键 (date, code) 覆盖旧数据）。

    参数:
        records  DailyKline 对象列表
        db_path  目标数据库文件路径

    返回:
        int  实际写入（插入或替换）的记录数

    示例:
        klines = fetch_daily_kline(code="sz.000001")
        count  = save_daily_kline(klines, "/tmp/stock_data.db")
    """
    if not records:
        return 0

    conn = _get_conn(db_path)
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

def sync_stock_basic(
    db_path: str,
    code: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> int:
    """
    从远程 API 拉取 stock_basic 数据并同步到本地 SQLite。
    若数据库或表不存在则自动初始化。

    参数:
        db_path  本地数据库文件路径
        code     可选，按股票代码过滤
        status   可选，按上市状态过滤（"1"=上市，"0"=退市）
        limit    单次请求返回的最大记录数，默认 100
        offset   分页偏移量，默认 0

    返回:
        int  写入记录数

    示例:
        # 全量同步所有上市股票基础信息
        sync_stock_basic("/tmp/stock_data.db", status="1")
        # 分页同步
        sync_stock_basic("/tmp/stock_data.db", limit=200, offset=400)
    """
    init_db(db_path)
    records = fetch_stock_basic(code=code, status=status, limit=limit, offset=offset)
    syn_count = save_stock_basic(records, db_path)
    print("股票基础信息已经同步")
    return syn_count


def sync_daily_kline(
    db_path: str,
    code: Optional[str] = None,
    date: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> int:
    """
    从远程 API 拉取 daily_kline 数据并同步到本地 SQLite。
    若数据库或表不存在则自动初始化。

    参数:
        db_path  本地数据库文件路径
        code     可选，按股票代码过滤
        date     可选，按具体日期过滤
        limit    单次请求返回的最大记录数，默认 100
        offset   分页偏移量，默认 0

    返回:
        int  写入记录数

    示例:
        # 同步某只股票行情
        sync_daily_kline("/tmp/stock_data.db", code="sz.000001")
        # 同步某天全市场行情，分页
        sync_daily_kline("/tmp/stock_data.db", date="2024-06-03", limit=200, offset=0)
    """
    init_db(db_path)
    records = fetch_daily_kline(code=code, date=date, limit=limit, offset=offset)
    syn_count = save_daily_kline(records, db_path)
    print("股票日线行情信息已经同步条")
    return syn_count


# ============================================================
# 本地 SQLite 查询接口
# ============================================================

def query_stock_basic(
    db_path: str,
    code: Optional[str] = None,
    status: Optional[str] = None,
    industry: Optional[str] = None,
    area: Optional[str] = None,
    market: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
) -> List[StockBasic]:
    """
    从本地 SQLite 数据库查询 stock_basic 表，返回 StockBasic 对象列表。

    参数:
        db_path   数据库文件路径
        code      按股票代码精确过滤
        status    按上市状态过滤（"1"=上市，"0"=退市）
        industry  按行业名称精确过滤
        area      按地区精确过滤
        market    按市场精确过滤
        limit     返回最大记录数；为 None 表示不限
        offset    分页偏移量，默认 0

    返回:
        List[StockBasic]  符合条件的股票基础信息对象列表

    示例:
        all_stocks   = query_stock_basic("/tmp/stock_data.db")
        bank_stocks  = query_stock_basic("/tmp/stock_data.db", industry="银行")
        single_stock = query_stock_basic("/tmp/stock_data.db", code="sz.000001")
    """
    
    conditions = []
    params: list = []

    if code is not None:
        conditions.append("code = ?")
        params.append(code)
    if status is not None:
        conditions.append("status = ?")
        params.append(status)
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

    conn = _get_conn(db_path)
    try:
        cursor = conn.execute(sql, params)
        rows = cursor.fetchall()
        # print("[query_stock_basic] sql:",sql, "params:",params)
        return [StockBasic.from_dict(dict(row)) for row in rows]
    finally:
        conn.close()


def query_daily_kline(
    db_path: str,
    code: Optional[str] = None,
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
        db_path     数据库文件路径
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
        klines = query_daily_kline("/tmp/stock_data.db", code="sz.000001")

        # 查询某只股票某段时间行情，最新的 30 条
        klines = query_daily_kline("/tmp/stock_data.db", code="sz.000001",
                                   start_date="2024-01-01", end_date="2024-12-31",
                                   limit=30, order_by="date DESC")

        # 查询某天全市场行情
        klines = query_daily_kline("/tmp/stock_data.db", date="2024-06-03")
    """
    conditions = []
    params: list = []

    if code is not None:
        conditions.append("code = ?")
        params.append(code)
    if date is not None:
        conditions.append("date = ?")
        params.append(date)
    else:
        if start_date is not None:
            conditions.append("date >= ?")
            params.append("'DATE({0})'".format(start_date))
        elif end_date is not None:
            conditions.append("date <= ?")
            params.append("'DATE({0})'".format(end_date))

    sql = "SELECT * FROM daily_kline"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += f" ORDER BY {order_by}"
    if limit is not None:
        sql += f" LIMIT {int(limit)} OFFSET {int(offset)}"

    conn = _get_conn(db_path)
    try:
        cursor = conn.execute(sql, params)
        rows = cursor.fetchall()
        # print("[query_daily_kline] sql:",sql, "params:",params, "rows:", len(rows))
        return [DailyKline.from_dict(dict(row)) for row in rows]
    finally:
        conn.close()

if __name__ == "__main__":
    print("数据库路径:",DB_PATH)
    sync_stock_basic(DB_PATH,offset=0, limit=10000)
    sync_daily_kline(DB_PATH, offset=0, limit=10000)