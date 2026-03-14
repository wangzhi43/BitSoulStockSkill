# StockApi 接口文档

`StockApi` 是项目对外提供的唯一数据与回测接口，封装了股票基础信息查询、K线数据获取、技术指标计算、性能指标计算和回测工具函数。

```python
from stock_api import StockApi
api = StockApi()
```

---

## 目录

1. [初始化](#初始化)
2. [股票基础信息](#股票基础信息)
3. [价格行情](#价格行情)
4. [技术指标（带缓存）](#技术指标带缓存)
5. [性能指标](#性能指标)
6. [回测工具](#回测工具)
7. [回测引擎控制](#回测引擎控制)
8. [策略辅助函数](#策略辅助函数)
9. [数据库维护](#数据库维护)

---

## 初始化

### 初始化 StockApi，自动初始化技术指标缓存数据库

```python
api = StockApi()
# __init__(self)
```

---

## 股票基础信息

### 获取所有股票代码列表

```python
symbols = api.get_all_symbols()
# get_all_symbols() -> List[str]
```

| 返回 | 说明 |
|------|------|
| `List[str]` | 股票代码列表，格式如 `['000001.SZ', '600519.SH', ...]` |

---

### 根据股票代码获取股票基础信息

```python
info = api.get_symbol_basic_infomation('600519.SH')
# get_symbol_basic_infomation(ts_code: str) -> Optional[StockBasic]
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `ts_code` | `str` | 股票代码，如 `000001.SZ` |

| 返回 | 说明 |
|------|------|
| `StockBasic` \| `None` | 股票基础信息，未查询到返回 `None` |

---

## 价格行情

### 查询每日基本面指标列表，支持按股票、日期、分页过滤

```python
# 查询某只股票全部历史基本面数据
basics = api.get_daily_basic(ts_codes=["000001.SZ"])

# 查询某天全市场基本面数据
basics = api.get_daily_basic(trade_date="2024-06-03")

# get_daily_basic(ts_codes=[], trade_date=None, start_date=None,
#                 end_date=None, limit=None, offset=0,
#                 order_by="trade_date ASC") -> List[DailyBasic]
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `ts_codes` | `List[str]` | `[]` | 按股票代码列表过滤，空表示不过滤 |
| `trade_date` | `str \| None` | `None` | 精确过滤交易日期，格式 `YYYY-MM-DD` |
| `start_date` | `str \| None` | `None` | 日期范围下限（含），格式 `YYYY-MM-DD` |
| `end_date` | `str \| None` | `None` | 日期范围上限（含），格式 `YYYY-MM-DD` |
| `limit` | `int \| None` | `None` | 返回最大记录数，`None` 表示不限 |
| `offset` | `int` | `0` | 分页偏移量 |
| `order_by` | `str` | `"trade_date ASC"` | 排序表达式 |

---

### 获取股票日线行情，按日期升序

```python
klines = api.get_daily_kline(['600519.SH'], '2026-01-01', '2026-03-01')
# get_daily_kline(symbols: List[str], start_date: str, end_date: str) -> List[DailyKline]
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `symbols` | `List[str]` | 股票代码列表，空表示获取所有股票 |
| `start_date` | `str` | 起始日期，格式 `YYYY-MM-DD` |
| `end_date` | `str` | 结束日期，格式 `YYYY-MM-DD` |

---

### 获取股票小时线行情，按日期和时间升序

```python
klines = api.get_hour_kline(['600519.SH'], '2026-01-01', '2026-03-01')
# get_hour_kline(symbols: List[str], start_date: str, end_date: str) -> List[HourKline]
```

---

### 获取股票周线行情，按日期升序

```python
klines = api.get_weekly_kline(['600519.SH'], '2026-01-01', '2026-03-01')
# get_weekly_kline(symbols: List[str], start_date: str, end_date: str) -> List[WeeklyKline]
```

---

### 获取股票月线行情，按日期升序

```python
klines = api.get_monthly_kline(['600519.SH'], '2026-01-01', '2026-03-01')
# get_monthly_kline(symbols: List[str], start_date: str, end_date: str) -> List[MonthlyKline]
```

---

### 获取指定股票的日线收盘价列表，按日期升序

```python
prices = api.get_daily_close_prices('600519.SH', '2026-01-01', '2026-03-01')
# get_daily_close_prices(code: str, start_date: str, end_date: str) -> List[float]
```

---

### 获取指定股票的日线开盘价列表

```python
prices = api.get_daily_open_prices('600519.SH', '2026-01-01', '2026-03-01')
# get_daily_open_prices(code: str, start_date: str, end_date: str) -> List[float]
```

---

### 获取指定股票的日线最高价列表

```python
prices = api.get_daily_high_prices('600519.SH', '2026-01-01', '2026-03-01')
# get_daily_high_prices(code: str, start_date: str, end_date: str) -> List[float]
```

---

### 获取指定股票的日线最低价列表

```python
prices = api.get_daily_low_prices('600519.SH', '2026-01-01', '2026-03-01')
# get_daily_low_prices(code: str, start_date: str, end_date: str) -> List[float]
```

---

### 获取指定股票的日线成交量列表

```python
volumes = api.get_daily_volumes('600519.SH', '2026-01-01', '2026-03-01')
# get_daily_volumes(code: str, start_date: str, end_date: str) -> List[float]
```

---

### 获取指定股票的日线涨跌幅列表（单位：%）

```python
pct = api.get_daily_pct_chg('600519.SH', '2026-01-01', '2026-03-01')
# get_daily_pct_chg(code: str, start_date: str, end_date: str) -> List[float]
```

---

### 获取指定日期的 Tick 级数据（模拟级），包含开高低收量额

```python
tick = api.get_tick_data('600519.SH', '2026-03-01')
# get_tick_data(code: str, date: str) -> Optional[Dict]
```

| 返回字段 | 说明 |
|----------|------|
| `time` | 时间 |
| `open` | 开盘价 |
| `high` | 最高价 |
| `low` | 最低价 |
| `close` | 收盘价 |
| `volume` | 成交量 |
| `amount` | 成交额 |

---

### 获取实时 Bar 数据，与 get_tick_data 等价，用于实盘级接口

```python
bar = api.get_realtime_bar('600519.SH', '2026-03-01')
# get_realtime_bar(code: str, date: str) -> Dict
```

---

## 技术指标（带缓存）

### 获取简单移动平均 SMA

```python
sma = api.get_sma('600519.SH', '2026-03-01', 20)
# get_sma(code: str, date: str, period: int = 20) -> Optional[float]
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `period` | `20` | 计算周期 |

---

### 获取指数移动平均 EMA

```python
ema = api.get_ema('600519.SH', '2026-03-01', 12)
# get_ema(code: str, date: str, period: int = 12) -> Optional[float]
```

---

### 获取相对强弱指标 RSI，值域 0~100，低于 30 超卖，高于 70 超买

```python
rsi = api.get_rsi('600519.SH', '2026-03-01', 14)
if rsi and rsi < 30:
    print('超卖')
# get_rsi(code: str, date: str, period: int = 14) -> Optional[float]
```

---

### 获取布林带指标，返回上轨、中轨、下轨

```python
bb = api.get_bollinger_bands('600519.SH', '2026-03-01')
if bb and close > bb['upper']:
    print('突破上轨')
# get_bollinger_bands(code: str, date: str, period: int = 20, std_dev: int = 2) -> Optional[Dict]
```

| 返回字段 | 说明 |
|----------|------|
| `upper` | 上轨 |
| `middle` | 中轨 |
| `lower` | 下轨 |

---

### 获取 MACD 指标，返回 MACD 线、信号线、柱状图

```python
macd = api.get_macd('600519.SH', '2026-03-01')
if macd and macd['histogram'] > 0:
    print('多头')
# get_macd(code: str, date: str, fast: int = 12, slow: int = 26, signal: int = 9) -> Optional[Dict]
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `fast` | `12` | 快线周期 |
| `slow` | `26` | 慢线周期 |
| `signal` | `9` | 信号线周期 |

| 返回字段 | 说明 |
|----------|------|
| `macd` | MACD 线 |
| `signal` | 信号线 |
| `histogram` | 柱状图（MACD - Signal） |

---

### 获取平均真实波幅 ATR，衡量价格波动性

```python
atr = api.get_atr('600519.SH', '2026-03-01', 14)
# get_atr(code: str, date: str, period: int = 14) -> Optional[float]
```

---

## 性能指标

### 计算最大回撤，返回回撤比例及对应的峰值、谷值索引

```python
dd, peak_idx, drawdown_idx = api.get_max_drawdown([1000000, 1100000, 950000])
print(f'最大回撤: {dd:.2%}')
# get_max_drawdown(equity_curve: List[float]) -> tuple
```

---

### 获取最大回撤百分比，如 0.15 表示 15%

```python
pct = api.get_max_drawdown_pct([1000000, 1100000, 950000])
# get_max_drawdown_pct(equity_curve: List[float]) -> float
```

---

### 计算年化收益率

```python
annualized = api.get_annualized_return(0.15, 60)
# get_annualized_return(total_return: float, days: int) -> float
```

| 参数 | 说明 |
|------|------|
| `total_return` | 总收益率，如 `0.15` 表示 15% |
| `days` | 交易天数 |

---

### 计算总收益率

```python
ret = api.get_total_return(1000000, 1150000)
# get_total_return(initial_value: float, final_value: float) -> float
```

---

### 计算夏普比率，衡量单位风险的超额收益

```python
sharpe = api.get_sharpe_ratio([1000000, 1050000, 1020000])
# get_sharpe_ratio(equity_curve: List[float], risk_free_rate: float = 0.03) -> float
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `risk_free_rate` | `0.03` | 无风险利率（年化） |

---

### 计算胜率（0~100），盈利交易次数占比

```python
trades = [{'profit': 1000}, {'profit': -500}, {'profit': 800}]
win_rate = api.get_win_rate(trades)
# get_win_rate(trades: List[Dict]) -> float
```

---

### 计算盈亏比，平均盈利 / 平均亏损

```python
ratio = api.get_profit_loss_ratio(trades)
# get_profit_loss_ratio(trades: List[Dict]) -> float
```

---

### 计算卡尔玛比率，年化收益 / 最大回撤

```python
calmar = api.get_calmar_ratio(equity_curve, 252)
# get_calmar_ratio(equity_curve: List[float], days: int) -> float
```

---

### 计算年化波动率，衡量收益稳定性

```python
vol = api.get_volatility(equity_curve)
# get_volatility(equity_curve: List[float]) -> float
```

---

### 获取完整交易统计信息

```python
stats = api.get_trade_stats(trades)
# get_trade_stats(trades: List[Dict]) -> Dict
```

| 返回字段 | 说明 |
|----------|------|
| `total_trades` | 总交易次数 |
| `wins` | 盈利次数 |
| `losses` | 亏损次数 |
| `win_rate` | 胜率 |
| `profit_loss_ratio` | 盈亏比 |
| `total_profit` | 总盈利 |
| `total_loss` | 总亏损 |
| `avg_profit` | 平均盈利 |
| `avg_loss` | 平均亏损 |

---

### 生成完整回测报告，汇总所有关键绩效指标

```python
equity = [1000000, 1050000, 1020000]
trades = [{'profit': 5000}, {'profit': -3000}]
report = api.calculate_metrics(equity, trades, 1000000, 30)
print(f"收益率: {report['total_return_pct']:.2f}%")
print(f"夏普比率: {report['sharpe_ratio']:.2f}")
# calculate_metrics(equity_curve: List[float], trades: List[Dict],
#                   initial_cash: float, days: int) -> Dict
```

| 返回字段 | 说明 |
|----------|------|
| `initial_cash` | 初始资金 |
| `final_value` | 最终资金 |
| `total_return` | 总收益率 |
| `total_return_pct` | 总收益率(%) |
| `annualized_return` | 年化收益率 |
| `annualized_return_pct` | 年化收益率(%) |
| `max_drawdown` | 最大回撤 |
| `max_drawdown_pct` | 最大回撤(%) |
| `sharpe_ratio` | 夏普比率 |
| `calmar_ratio` | 卡尔玛比率 |
| `volatility` | 波动率 |
| `trading_days` | 交易天数 |
| `trade_stats` | 交易统计（同 `get_trade_stats`） |

---

## 回测工具

### 模拟单笔交易，计算成本、手续费和净收款

```python
result = api.simulate_trade('BUY', 100.0, 100)
print(f"成本: {result['cost']}, 手续费: {result['fee']}")
# simulate_trade(action: str, price: float, quantity: int, fee_rate: float = 0.0003) -> Dict
```

| 返回字段 | 说明 |
|----------|------|
| `cost` | 成本 |
| `fee` | 手续费 |
| `net_proceeds` | 净收款（卖出时） |

---

### 计算交易成本，含手续费和滑点

```python
cost = api.calculate_trade_cost('BUY', 100.0, 100, 0.0003, 0.001)
# calculate_trade_cost(action, price, quantity, fee_rate=0.0003, slippage=0.0) -> float
```

---

### 创建持仓对象，记录股票、股数、买入价和日期

```python
pos = api.create_position('600519.SH', 100, 1800.0, '2026-01-01')
# create_position(code: str, shares: int, price: float, date: str) -> Position
```

---

### 计算持仓市值

```python
value = api.get_position_value(pos, 1900.0)
# get_position_value(position: Position, current_price: float) -> float
```

---

### 计算持仓盈亏，返回盈亏金额和比例

```python
profit, pct = api.get_position_profit(position, 2000.0)
print(f"盈利: {profit}, 比例: {pct:.2%}")
# get_position_profit(position: Position, current_price: float) -> tuple
```

---

### 计算组合总价值（现金 + 所有持仓市值）

```python
value = api.calculate_portfolio_value(500000, positions, current_prices)
# calculate_portfolio_value(cash: float, positions: Dict[str, Position],
#                           prices: Dict[str, float]) -> float
```

---

### 获取组合持仓详情列表

```python
details = api.get_portfolio_positions(positions)
# get_portfolio_positions(positions: Dict[str, Position]) -> List[Dict]
```

---

### 从每日资产列表构建权益曲线

```python
values = [('2026-01-01', 1000000), ('2026-01-02', 1005000)]
curve = api.build_equity_curve(values)
# build_equity_curve(daily_values: List[tuple]) -> List[float]
```

---

### 计算日收益率序列

```python
returns = api.calculate_daily_returns(equity_curve)
# calculate_daily_returns(equity_curve: List[float]) -> List[float]
```

---

### 买入信号判断：MA 金叉且 RSI 超卖时返回 True

```python
if api.should_buy(close, ma5, ma20, rsi, 30):
    print('买入信号')
# should_buy(current_price, ma_short, ma_long, rsi=50, rsi_oversold=30) -> bool
```

---

### 卖出信号判断：MA 死叉或 RSI 超买时返回 True

```python
if api.should_sell(close, ma5, ma20, rsi, 70):
    print('卖出信号')
# should_sell(current_price, ma_short, ma_long, rsi=50, rsi_overbought=70) -> bool
```

---

### 计算权益曲线的逐日回撤序列

```python
drawdowns = api.calculate_drawdown([1000000, 1100000, 950000])
# calculate_drawdown(equity_curve: List[float]) -> List[float]
```

---



## 回测引擎控制

### 初始化回测环境，返回含现金、持仓、订单、交易记录的状态字典

```python
env = api.init_backtest(1000000, 0.0003)
# init_backtest(initial_cash: float = 1000000.0, fee_rate: float = 0.0003) -> Dict
```

| 返回字段 | 说明 |
|----------|------|
| `initial_cash` | 初始资金 |
| `fee_rate` | 手续费率 |
| `cash` | 当前现金 |
| `positions` | 持仓字典 |
| `orders` | 订单列表 |
| `trades` | 交易记录 |
| `equity_curve` | 权益曲线 |

---

### 执行买入操作，自动更新 env 中的现金、持仓和交易记录

```python
result = api.execute_buy(env, '600519.SH', 1800.0, 100, '2026-01-01')
# execute_buy(env, code, price, quantity, date) -> Dict
```

| 返回字段 | 说明 |
|----------|------|
| `success` | 是否成功 |
| `cost` | 成本 |
| `fee` | 手续费 |
| `reason` | 失败原因（失败时） |

---

### 执行卖出操作，自动更新 env

```python
result = api.execute_sell(env, '600519.SH', 1900.0, 100)
# execute_sell(env, code, price, quantity) -> Dict
```

| 返回字段 | 说明 |
|----------|------|
| `success` | 是否成功 |
| `net_proceeds` | 净收款 |
| `fee` | 手续费 |
| `reason` | 失败原因（失败时） |

---

### 获取当前总权益（现金 + 持仓市值）

```python
equity = api.get_equity(env, current_prices)
# get_equity(env: Dict, current_prices: Dict[str, float]) -> float
```

---

### 将当日权益追加记录到 env['equity_curve']

```python
api.record_equity(env, '2026-03-01', current_prices)
# record_equity(env, date, current_prices) -> None
```

---

### 开仓，买入建立多头持仓

```python
pos = api.open_position('600519.SH', 1800.0, 100, '2026-01-01')
# open_position(code, price, quantity, date) -> Position
```

---

### 平仓，卖出结束多头持仓，返回盈亏和持有天数

```python
result = api.close_position(position, 1900.0, '2026-01-15')
print(f"盈利: {result['profit']}")
# close_position(position, price, date) -> Dict
```

| 返回字段 | 说明 |
|----------|------|
| `profit` | 盈亏金额 |
| `profit_pct` | 盈亏比例 |
| `hold_days` | 持有天数 |

---

### 更新持仓的当前价格，用于实时市值计算

```python
api.update_position_price(position, 1900.0)
# update_position_price(position, current_price) -> None
```

---

### 创建本地模拟订单（非真实下单）

```python
order = api.create_order('600519.SH', 'BUY', 1800.0, 100)
# create_order(code, action, price, quantity) -> Dict
```

| 返回字段 | 说明 |
|----------|------|
| `order_id` | 订单 ID |
| `status` | 状态（`PENDING`） |
| `create_time` | 创建时间 |

---

### 取消订单，仅 PENDING 状态可取消

```python
success = api.cancel_order(order)
# cancel_order(order: Dict) -> bool
```

---

### 获取订单状态：PENDING / FILLED / CANCELLED / REJECTED

```python
status = api.get_order_status(order)
# get_order_status(order: Dict) -> str
```

---

## 策略辅助函数

### 计算指定股票近 N 日平均涨幅（%）

```python
avg_change = api.get_price_change_rate('600519.SH', '2026-03-01', 3)
# get_price_change_rate(code, date, days=3) -> Optional[float]
```

---

### 从股票列表中筛选出近 N 日涨幅最高的前 N 只，按涨幅降序返回

```python
top_stocks = api.get_top_performers(codes, '2026-03-01', 3, 3)
# [(code, avg_pct), ...]
# get_top_performers(codes, date, days=3, top_n=3) -> List[tuple]
```

---

### 获取指定日期的收盘价，无数据返回 None

```python
price = api.get_price_at_date('600519.SH', '2026-03-01')
# get_price_at_date(code, date) -> Optional[float]
```

---

### 批量获取多个日期的收盘价，按日期升序对齐

```python
prices = api.get_prices_at_dates('600519.SH', ['2026-01-01', '2026-01-02'])
# get_prices_at_dates(code, dates) -> List[Optional[float]]
```

---

## 数据库维护

### 初始化所有数据库（指标缓存库等）

```python
api.init_databases()
# init_databases() -> None
```

---

### 清除技术指标缓存，可指定股票或清除全部

```python
api.clear_indicator_cache('600519.SH')  # 清除指定股票
api.clear_indicator_cache()             # 清除所有
# clear_indicator_cache(code: str = None) -> None
```
