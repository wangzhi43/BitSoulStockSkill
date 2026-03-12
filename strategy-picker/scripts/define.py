import os
import utils
# ============================================================
# 常量
# ============================================================

BASE_URL = "http://139.224.210.110:80"  # 每次 HTTP 请求拉取的最大记录数（服务端允许范围内取较大值以减少请求次数）
HTTP_TIMEOUT = 30     # HTTP 请求超时秒数
DB_PATH = os.path.join(utils.get_skill_work_dir(), "data.db")

# ============================================================
# 数据模型
# ============================================================

class StockBasic:
    """
    股票基础信息，对应远程 stock_basic 表及本地同名表。

    字段说明:
        ts_code     股票代码，如 000001.SZ
        symbol      股票符号，如 000001
        name        股票名称，如 平安银行
        area        所在地区
        industry    所属行业
        fullname    股票全称
        enname      英文名称
        cnspell     拼音
        market      市场类型（主板/创业板/科创板等）
        exchange    交易所代码
        curr_type   交易货币
        list_date   上市日期
        delist_date 退市日期（未退市则为空）
        is_hs       是否沪深港通标的（N=否, H=沪股通, S=深股通）
    """

    __slots__ = ("ts_code", "symbol", "name", "area", "industry",
                 "fullname", "enname", "cnspell", "market", "exchange",
                 "curr_type", "list_date", "delist_date", "is_hs")

    def __init__(self, ts_code: str, symbol: str, name: str,
                 area: str, industry: str, fullname: str, enname: str,
                 cnspell: str, market: str, exchange: str, curr_type: str,
                 list_date: str, delist_date: str, is_hs: str):
        self.ts_code = ts_code
        self.symbol = symbol
        self.name = name
        self.area = area
        self.industry = industry
        self.fullname = fullname
        self.enname = enname
        self.cnspell = cnspell
        self.market = market
        self.exchange = exchange
        self.curr_type = curr_type
        self.list_date = list_date
        self.delist_date = delist_date
        self.is_hs = is_hs

    @classmethod
    def from_dict(cls, d: dict) -> "StockBasic":
        """从字典（API 响应或数据库行）构造 StockBasic 对象。"""
        return cls(
            ts_code=d.get("ts_code") or "",
            symbol=d.get("symbol") or "",
            name=d.get("name") or "",
            area=d.get("area") or "",
            industry=d.get("industry") or "",
            fullname=d.get("fullname") or "",
            enname=d.get("enname") or "",
            cnspell=d.get("cnspell") or "",
            market=d.get("market") or "",
            exchange=d.get("exchange") or "",
            curr_type=d.get("curr_type") or "",
            list_date=d.get("list_date") or "",
            delist_date=d.get("delist_date") or "",
            is_hs=d.get("is_hs") or "",
        )

    def __repr__(self) -> str:
        return f"StockBasic(ts_code={self.ts_code!r}, name={self.name!r}, market={self.market!r})"


class DailyKline:
    """
    日线行情数据，对应远程 daily_kline 表及本地同名表。

    字段说明:
        date        交易日期，格式 YYYY-MM-DD
        code        股票代码，如 sz.000001
        open        开盘价
        high        最高价
        low         最低价
        close       收盘价
        volume      成交量（股）
        amount      成交额（元）
        adjustflag  复权状态
        turn        换手率
        pctChg      涨跌幅（%）
        pre_close   前收盘价
        change      涨跌额
    """

    __slots__ = ("date", "code", "open", "high", "low", "close",
                 "volume", "amount", "adjustflag", "turn", "pctChg",
                 "pre_close", "change")

    def __init__(self, date: str, code: str, open: float, high: float,
                 low: float, close: float, volume: float, amount: float,
                 adjustflag: str, turn: float, pctChg: float,
                 pre_close: float, change: float):
        self.date = date
        self.code = code
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume
        self.amount = amount
        self.adjustflag = adjustflag
        self.turn = turn
        self.pctChg = pctChg
        self.pre_close = pre_close
        self.change = change

    @classmethod
    def from_dict(cls, d: dict) -> "DailyKline":
        """从字典（API 响应或数据库行）构造 DailyKline 对象。"""
        def _f(v):
            """将值安全转换为 float，None/空字符串返回 0.0。"""
            try:
                return float(v) if v is not None and v != "" else 0.0
            except (TypeError, ValueError):
                return 0.0

        return cls(
            date=d.get("date") or "",
            code=d.get("code") or "",
            open=_f(d.get("open")),
            high=_f(d.get("high")),
            low=_f(d.get("low")),
            close=_f(d.get("close")),
            volume=_f(d.get("volume")),
            amount=_f(d.get("amount")),
            adjustflag=d.get("adjustflag") or "",
            turn=_f(d.get("turn")),
            pctChg=_f(d.get("pctChg")),
            pre_close=_f(d.get("pre_close")),
            change=_f(d.get("change")),
        )

    def __repr__(self) -> str:
        return (f"DailyKline(date={self.date!r}, code={self.code!r}, "
                f"close={self.close}, pctChg={self.pctChg})")

