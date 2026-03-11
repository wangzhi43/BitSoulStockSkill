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
        code        股票代码，如 sz.000001
        code_name   股票名称，如 平安银行
        pinyin      股票名称拼音首字母
        ipoDate     上市日期
        outDate     退市日期（未退市则为空）
        type        股票类型
        status      上市状态：L=上市，0=退市
        industry    所属行业
        area        所在地区
        market      所在市场
    """

    __slots__ = ("code", "code_name", "pinyin", "ipoDate", "outDate",
                 "type", "status", "industry", "area", "market")

    def __init__(self, code: str, code_name: str, pinyin: str,
                 ipoDate: str, outDate: str, type: str, status: str,
                 industry: str, area: str, market: str):
        self.code = code
        self.code_name = code_name
        self.pinyin = pinyin
        self.ipoDate = ipoDate
        self.outDate = outDate
        self.type = type
        self.status = status
        self.industry = industry
        self.area = area
        self.market = market

    @classmethod
    def from_dict(cls, d: dict) -> "StockBasic":
        """从字典（API 响应或数据库行）构造 StockBasic 对象。"""
        return cls(
            code=d.get("code") or "",
            code_name=d.get("code_name") or "",
            pinyin=d.get("pinyin") or "",
            ipoDate=d.get("ipoDate") or "",
            outDate=d.get("outDate") or "",
            type=d.get("type") or "",
            status=d.get("status") or "",
            industry=d.get("industry") or "",
            area=d.get("area") or "",
            market=d.get("market") or "",
        )

    def __repr__(self) -> str:
        return f"StockBasic(code={self.code!r}, code_name={self.code_name!r}, status={self.status!r})"


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

