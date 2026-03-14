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
        list_status 上市状态 (L=上市, D=退市, G=过会未交易, P=暂停上市)
        delist_date 退市日期（未退市则为空）
        is_hs       是否沪深港通标的（N=否, H=沪股通, S=深股通）
    """

    __slots__ = ("ts_code", "symbol", "name", "area", "industry",
                 "fullname", "enname", "cnspell", "market", "exchange",
                 "curr_type", "list_date", "list_status", "delist_date", "is_hs")

    def __init__(self, ts_code: str, symbol: str, name: str,
                 area: str, industry: str, fullname: str, enname: str,
                 cnspell: str, market: str, exchange: str, curr_type: str,
                 list_date: str, list_status:str, delist_date: str, is_hs: str):
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
        self.list_status = list_status
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
            list_status=d.get("list_status") or "",
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


class HourKline:
    """
    小时级别 K 线行情数据，对应本地 hour_kline 表。

    字段说明:
        date    交易日期
        time    交易时间
        open    开盘价
        high    最高价
        low     最低价
        close   收盘价
        volume  成交量
        amount  成交额
        code    股票代码
    """

    __slots__ = ("date", "time", "open", "high", "low", "close",
                 "volume", "amount", "code")

    def __init__(self, date: str, time: str, open: float, high: float,
                 low: float, close: float, volume: float, amount: float,
                 code: str):
        self.date = date
        self.time = time
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume
        self.amount = amount
        self.code = code

    @classmethod
    def from_dict(cls, d: dict) -> "HourKline":
        def _f(v):
            try:
                return float(v) if v is not None and v != "" else 0.0
            except (TypeError, ValueError):
                return 0.0

        return cls(
            date=d.get("date") or "",
            time=d.get("time") or "",
            open=_f(d.get("open")),
            high=_f(d.get("high")),
            low=_f(d.get("low")),
            close=_f(d.get("close")),
            volume=_f(d.get("volume")),
            amount=_f(d.get("amount")),
            code=d.get("code") or "",
        )

    def __repr__(self) -> str:
        return (f"HourKline(date={self.date!r}, time={self.time!r}, "
                f"code={self.code!r}, close={self.close})")


class WeeklyKline:
    """
    周线行情数据，对应本地 weekly_kline 表。

    字段说明:
        date    交易日期（周五日期）
        code    股票代码
        open    开盘价
        high    最高价
        low     最低价
        close   收盘价
        volume  成交量
        amount  成交额
        pctChg  涨跌幅（%）
    """

    __slots__ = ("date", "code", "open", "high", "low", "close",
                 "volume", "amount", "pctChg")

    def __init__(self, date: str, code: str, open: float, high: float,
                 low: float, close: float, volume: float, amount: float,
                 pctChg: float):
        self.date = date
        self.code = code
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume
        self.amount = amount
        self.pctChg = pctChg

    @classmethod
    def from_dict(cls, d: dict) -> "WeeklyKline":
        def _f(v):
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
            pctChg=_f(d.get("pctChg")),
        )

    def __repr__(self) -> str:
        return (f"WeeklyKline(date={self.date!r}, code={self.code!r}, "
                f"close={self.close}, pctChg={self.pctChg})")


class MonthlyKline:
    """
    月线行情数据，对应本地 monthly_kline 表。

    字段说明:
        date    交易日期（月末日期）
        code    股票代码
        open    开盘价
        high    最高价
        low     最低价
        close   收盘价
        volume  成交量
        amount  成交额
        pctChg  涨跌幅（%）
    """

    __slots__ = ("date", "code", "open", "high", "low", "close",
                 "volume", "amount", "pctChg")

    def __init__(self, date: str, code: str, open: float, high: float,
                 low: float, close: float, volume: float, amount: float,
                 pctChg: float):
        self.date = date
        self.code = code
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume
        self.amount = amount
        self.pctChg = pctChg

    @classmethod
    def from_dict(cls, d: dict) -> "MonthlyKline":
        def _f(v):
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
            pctChg=_f(d.get("pctChg")),
        )

    def __repr__(self) -> str:
        return (f"MonthlyKline(date={self.date!r}, code={self.code!r}, "
                f"close={self.close}, pctChg={self.pctChg})")


class DailyBasic:
    """
    每日基本面指标数据，对应本地 daily_basic 表。

    字段说明:
        trade_date      交易日期（PK）
        ts_code         股票代码（PK）
        close           当日收盘价
        turnover_rate   换手率（%）
        turnover_rate_f 换手率（自由流通股）
        volume_ratio    量比
        pe              市盈率（总市值/净利润）
        pe_ttm          市盈率（TTM）
        pb              市净率（总市值/净资产）
        ps              市销率
        ps_ttm          市销率（TTM）
        dv_ratio        股息率（%）
        dv_ttm          股息率（TTM）（%）
        total_share     总股本（万股）
        float_share     流通股本（万股）
        free_share      自由流通股本（万）
        total_mv        总市值（万元）
        circ_mv         流通市值（万元）
        adj_factor      复权因子
    """

    __slots__ = ("trade_date", "ts_code", "close", "turnover_rate",
                 "turnover_rate_f", "volume_ratio", "pe", "pe_ttm",
                 "pb", "ps", "ps_ttm", "dv_ratio", "dv_ttm",
                 "total_share", "float_share", "free_share",
                 "total_mv", "circ_mv", "adj_factor")

    def __init__(self, trade_date: str, ts_code: str, close: float,
                 turnover_rate: float, turnover_rate_f: float, volume_ratio: float,
                 pe: float, pe_ttm: float, pb: float, ps: float, ps_ttm: float,
                 dv_ratio: float, dv_ttm: float, total_share: float,
                 float_share: float, free_share: float, total_mv: float,
                 circ_mv: float, adj_factor: float):
        self.trade_date = trade_date
        self.ts_code = ts_code
        self.close = close
        self.turnover_rate = turnover_rate
        self.turnover_rate_f = turnover_rate_f
        self.volume_ratio = volume_ratio
        self.pe = pe
        self.pe_ttm = pe_ttm
        self.pb = pb
        self.ps = ps
        self.ps_ttm = ps_ttm
        self.dv_ratio = dv_ratio
        self.dv_ttm = dv_ttm
        self.total_share = total_share
        self.float_share = float_share
        self.free_share = free_share
        self.total_mv = total_mv
        self.circ_mv = circ_mv
        self.adj_factor = adj_factor

    @classmethod
    def from_dict(cls, d: dict) -> "DailyBasic":
        def _f(v):
            try:
                return float(v) if v is not None and v != "" else 0.0
            except (TypeError, ValueError):
                return 0.0

        return cls(
            trade_date=d.get("trade_date") or "",
            ts_code=d.get("ts_code") or "",
            close=_f(d.get("close")),
            turnover_rate=_f(d.get("turnover_rate")),
            turnover_rate_f=_f(d.get("turnover_rate_f")),
            volume_ratio=_f(d.get("volume_ratio")),
            pe=_f(d.get("pe")),
            pe_ttm=_f(d.get("pe_ttm")),
            pb=_f(d.get("pb")),
            ps=_f(d.get("ps")),
            ps_ttm=_f(d.get("ps_ttm")),
            dv_ratio=_f(d.get("dv_ratio")),
            dv_ttm=_f(d.get("dv_ttm")),
            total_share=_f(d.get("total_share")),
            float_share=_f(d.get("float_share")),
            free_share=_f(d.get("free_share")),
            total_mv=_f(d.get("total_mv")),
            circ_mv=_f(d.get("circ_mv")),
            adj_factor=_f(d.get("adj_factor")),
        )

    def __repr__(self) -> str:
        return (f"DailyBasic(trade_date={self.trade_date!r}, ts_code={self.ts_code!r}, "
                f"close={self.close}, pe={self.pe}, pb={self.pb})")


class Income:
    """
    利润表数据，对应本地 income 表。

    字段说明:
        ts_code           股票代码（PK）
        end_date          报告期结束日期（PK）
        report_type       报告类型（PK，1=合并报表）
        ann_date          公告日期
        comp_type         公司类型
        basic_eps         基本每股收益
        diluted_eps       稀释每股收益
        total_revenue     营业总收入
        revenue           营业收入
        total_cogs        营业总成本
        oper_cost         营业成本
        sell_exp          销售费用
        admin_exp         管理费用
        fin_exp           财务费用
        total_profit      利润总额
        income_tax        所得税费用
        n_income          净利润
        n_income_attr_p   归属于母公司所有者的净利润
        minority_gain     少数股东损益
        oth_compr_income  其他综合收益
        t_compr_income    综合收益总额
        compr_inc_attr_p  归属于母公司所有者的综合收益总额
        ebit              息税前利润
        ebitda            息税折旧摊销前利润
        roe               净资产收益率（%）
        roa               总资产收益率（%）
        gross_margin      毛利率（%）
        net_profit_margin 净利率（%）
        net_profit_yoy    净利润增长率（%）
        revenue_yoy       营业收入增长率（%）
        equity_yoy        净资产增长率（%）
        pcf               市现率
        free_circ_mv      自由流通市值
    """

    __slots__ = (
        "ts_code", "end_date", "report_type", "ann_date", "comp_type",
        "basic_eps", "diluted_eps", "total_revenue", "revenue",
        "total_cogs", "oper_cost", "sell_exp", "admin_exp", "fin_exp",
        "total_profit", "income_tax", "n_income", "n_income_attr_p",
        "minority_gain", "oth_compr_income", "t_compr_income", "compr_inc_attr_p",
        "ebit", "ebitda", "roe", "roa", "gross_margin", "net_profit_margin",
        "net_profit_yoy", "revenue_yoy", "equity_yoy", "pcf", "free_circ_mv",
    )

    def __init__(
        self,
        ts_code: str, end_date: str, report_type: str, ann_date: str, comp_type: str,
        basic_eps: float, diluted_eps: float, total_revenue: float, revenue: float,
        total_cogs: float, oper_cost: float, sell_exp: float, admin_exp: float, fin_exp: float,
        total_profit: float, income_tax: float, n_income: float, n_income_attr_p: float,
        minority_gain: float, oth_compr_income: float, t_compr_income: float, compr_inc_attr_p: float,
        ebit: float, ebitda: float, roe: float, roa: float, gross_margin: float,
        net_profit_margin: float, net_profit_yoy: float, revenue_yoy: float,
        equity_yoy: float, pcf: float, free_circ_mv: float,
    ):
        self.ts_code = ts_code
        self.end_date = end_date
        self.report_type = report_type
        self.ann_date = ann_date
        self.comp_type = comp_type
        self.basic_eps = basic_eps
        self.diluted_eps = diluted_eps
        self.total_revenue = total_revenue
        self.revenue = revenue
        self.total_cogs = total_cogs
        self.oper_cost = oper_cost
        self.sell_exp = sell_exp
        self.admin_exp = admin_exp
        self.fin_exp = fin_exp
        self.total_profit = total_profit
        self.income_tax = income_tax
        self.n_income = n_income
        self.n_income_attr_p = n_income_attr_p
        self.minority_gain = minority_gain
        self.oth_compr_income = oth_compr_income
        self.t_compr_income = t_compr_income
        self.compr_inc_attr_p = compr_inc_attr_p
        self.ebit = ebit
        self.ebitda = ebitda
        self.roe = roe
        self.roa = roa
        self.gross_margin = gross_margin
        self.net_profit_margin = net_profit_margin
        self.net_profit_yoy = net_profit_yoy
        self.revenue_yoy = revenue_yoy
        self.equity_yoy = equity_yoy
        self.pcf = pcf
        self.free_circ_mv = free_circ_mv

    @classmethod
    def from_dict(cls, d: dict) -> "Income":
        """从字典（数据库行）构造 Income 对象。"""
        def _f(v):
            try:
                return float(v) if v is not None and v != "" else 0.0
            except (TypeError, ValueError):
                return 0.0

        return cls(
            ts_code=d.get("ts_code") or "",
            end_date=d.get("end_date") or "",
            report_type=d.get("report_type") or "",
            ann_date=d.get("ann_date") or "",
            comp_type=d.get("comp_type") or "",
            basic_eps=_f(d.get("basic_eps")),
            diluted_eps=_f(d.get("diluted_eps")),
            total_revenue=_f(d.get("total_revenue")),
            revenue=_f(d.get("revenue")),
            total_cogs=_f(d.get("total_cogs")),
            oper_cost=_f(d.get("oper_cost")),
            sell_exp=_f(d.get("sell_exp")),
            admin_exp=_f(d.get("admin_exp")),
            fin_exp=_f(d.get("fin_exp")),
            total_profit=_f(d.get("total_profit")),
            income_tax=_f(d.get("income_tax")),
            n_income=_f(d.get("n_income")),
            n_income_attr_p=_f(d.get("n_income_attr_p")),
            minority_gain=_f(d.get("minority_gain")),
            oth_compr_income=_f(d.get("oth_compr_income")),
            t_compr_income=_f(d.get("t_compr_income")),
            compr_inc_attr_p=_f(d.get("compr_inc_attr_p")),
            ebit=_f(d.get("ebit")),
            ebitda=_f(d.get("ebitda")),
            roe=_f(d.get("roe")),
            roa=_f(d.get("roa")),
            gross_margin=_f(d.get("gross_margin")),
            net_profit_margin=_f(d.get("net_profit_margin")),
            net_profit_yoy=_f(d.get("net_profit_yoy")),
            revenue_yoy=_f(d.get("revenue_yoy")),
            equity_yoy=_f(d.get("equity_yoy")),
            pcf=_f(d.get("pcf")),
            free_circ_mv=_f(d.get("free_circ_mv")),
        )

    def __repr__(self) -> str:
        return (f"Income(ts_code={self.ts_code!r}, end_date={self.end_date!r}, "
                f"report_type={self.report_type!r}, n_income={self.n_income})")
