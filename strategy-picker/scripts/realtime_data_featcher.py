import requests
import time
import json
import random
import re
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass

@dataclass
class RealtimeStockQuote:
    """
    实时股票报价信息
    """
    ts_code: str             # 股票代码（如 000001.SZ）
    name: str                # 股票名称
    open: float              # 今日开盘价
    pre_close: float         # 昨日收盘价
    price: float             # 当前最新价
    high: float              # 今日最高价
    low: float               # 今日最低价
    bid: float               # 买一价
    ask: float               # 卖一价
    volume: int              # 成交量（股）
    amount: float            # 成交额（元）
    date: str                # 交易日期（YYYY-MM-DD）
    time: str                # 最新报价时间（HH:MM:SS）
    amplitude: float         # 振幅（%）
    turnover_rate: Optional[float]  # 换手率（%），可能为空
    total_cap: Optional[float]      # 总市值（元），可能为空
    circ_cap: Optional[float]       # 流通市值（元），可能为空
    pb: Optional[float]             # 市净率，可能为空
    pe_ttm: Optional[float]         # 市盈率（TTM），可能为空
    total_shares: Optional[float]   # 总股本（股），可能为空
    circ_shares: Optional[float]    # 流通股本（股），可能为空
    status: str              # 请求状态（success / error）

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RealtimeStockQuote":
        return cls(**data)

class RealTimeDataFetcher:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.last_request_time = {}
        self.min_interval = 1.0  # Minimum int

    def _convert_to_sina_symbol(self, ts_code: str) -> str:
        # 000001.SZ -> sz000001
        # 600519.SH -> sh600519
        code, market = ts_code.split('.')
        return f"{market.lower()}{code}"
    
    def _wait_for_rate_limit(self, source: str):
        current_time = time.time()
        last_time = self.last_request_time.get(source, 0)
        elapsed = current_time - last_time
        if elapsed < self.min_interval:
            sleep_time = self.min_interval - elapsed
            time.sleep(sleep_time)
        self.last_request_time[source] = time.time()

    def request_stock_info(self, ts_code: str) -> Optional[RealtimeStockQuote]:
            """
            Fetch real-time data from Sina Finance.
            URL: http://hq.sinajs.cn/list={symbol}
            """
            self._wait_for_rate_limit('sina')
            symbol = self._convert_to_sina_symbol(ts_code)
            url = f"http://hq.sinajs.cn/list={symbol}"
            headers = self.headers.copy()
            headers['Referer'] = 'https://finance.sina.com.cn/'
            try:
                response = requests.get(url, headers=headers, timeout=5)
                response.raise_for_status()
                # Format: var hq_str_sh601006="大秦铁路, 27.55, 27.25, 26.91, 27.55, 26.20, 26.91, 26.92, ...";
                content = response.text
                match = re.search(r'="(.*)";', content)
                if match:
                    data_str = match.group(1)
                    parts = data_str.split(',')
                    if len(parts) > 30:
                        pre_close = float(parts[2])
                        high = float(parts[4])
                        low = float(parts[5])
                        amplitude = 0.0
                        if pre_close > 0:
                            amplitude = (high - low) / pre_close * 100

                        return RealtimeStockQuote(
                            ts_code=ts_code,
                            name=parts[0],
                            open=float(parts[1]),
                            pre_close=pre_close,
                            price=float(parts[3]),
                            high=high,
                            low=low,
                            bid=float(parts[6]),
                            ask=float(parts[7]),
                            volume=int(parts[8]),  # Sina returns shares
                            amount=float(parts[9]),
                            date=parts[30],
                            time=parts[31],
                            amplitude=round(amplitude, 2),
                            turnover_rate=None,
                            total_cap=None,
                            circ_cap=None,
                            pb=None,
                            pe_ttm=None,
                            total_shares=None,
                            circ_shares=None,
                            status="success"
                        )
                return None
            except Exception:
                return None
        

if __name__ == "__main__":
    RealTimeDataFetcher().fetch_sina("000001.SZ")
     
