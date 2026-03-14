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

### `__init__()`

初始化 `StockApi`，自动初始化技术指标缓存数据库。

```python
api = StockApi()
```

---

## 股票基础信息

### `get_all_symbols() -> List[str]`

获取所有股票代码列表。

| 返回 | 说明 |
|------|------|
| `List[str]` | 股票代码列表，格式如 `['000001.SZ', '600519.SH', ...]` |

```python
symbols = api.get_all_symbols()
```

---

### `get_symbol_basic_infomation(ts_code) -> Optional[StockBasic]`

根据股票代码获取股票基础信息。

| 参数 | 类型 | 说明 |
|------|------|------|
| `ts_code` | `str` | 股票代码，如 `000001.SZ` |

| 返回 | 说明 |
|------|------|
| `StockBasic` \| `None` | 股票基础信息，未查询到返回 `None` |

```python
info = api.get_symbol_basic_infomation('600519.SH')
```

---

## 价格行情

### `get_daily_basic(...) -> List[DailyBasic]`

查询每日基本面指标列表。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `ts_codes` | `List[str]` | `[]` | 按股票代码列表过滤，空表示不过滤 |
| `trade_date` | `str \| None` | `None` | 精确过滤交易日期，格式 `YYYY-MM-DD` |
| `start_date` | `str \| None` | `None` | 日期范围下限（含），格式 `YYYY-MM-DD` |
| `end_date` | `str \| None` | `None` | 日期范围上限（含），格式 `YYYY-MM-DD` |
| `limit` | `int \| None` | `None` | 返回最大记录数，`None` 表示不限 |
| `offset` | `int` | `0` | 分页偏移量 |
| `order_by` | `str` | `"trade_date ASC"` | 排序表达式 |

| 返回 | 说明 |
|------|------|
| `List[DailyBasic]` | 符合条件的每日基本面指标对象列表 |

```python
# 查询某只股票全部历史基本面数据
basics = api.get_daily_basic(ts_codes=["000001.SZ"])

# 查询某天全市场基本面数据
basics = api.get_daily_basic(trade_date="2024-06-03")
```

---

### `get_daily_kline(symbols, start_date, end_date) -> List[DailyKline]`

获取指定日期范围内的股票日线行情（按日期升序）。

| 参数 | 类型 | 说明 |
|------|------|------|
| `symbols` | `List[str]` | 股票代码列表，空表示获取所有股票 |
| `start_date` | `str` | 起始日期，格式 `YYYY-MM-DD` |
| `end_date` | `str` | 结束日期，格式 `YYYY-MM-DD` |

| 返回 | 说明 |
|------|------|
| `List[DailyKline]` | 日线行情列表，无数据返回空列表 |

```python
klines = api.get_daily_kline(['600519.SH'], '2026-01-01', '2026-03-01')
```

---

### `get_hour_kline(symbols, start_date, end_date) -> List[HourKline]`

获取指定日期范围内的股票小时线行情（按日期和时间升序）。

| 参数 | 类型 | 说明 |
|------|------|------|
| `symbols` | `List[str]` | 股票代码列表，空表示获取所有股票 |
| `start_date` | `str` | 起始日期 |
| `end_date` | `str` | 结束日期 |

| 返回 | 说明 |
|------|------|
| `List[HourKline]` | 小时线行情列表 |

---

### `get_weekly_kline(symbols, start_date, end_date) -> List[WeeklyKline]`

获取指定日期范围内的股票周线行情（按日期升序）。

| 参数 | 类型 | 说明 |
|------|------|------|
| `symbols` | `List[str]` | 股票代码列表 |
| `start_date` | `str` | 起始日期 |
| `end_date` | `str` | 结束日期 |

| 返回 | 说明 |
|------|------|
| `List[WeeklyKline]` | 周线行情列表 |

---

### `get_monthly_kline(symbols, start_date, end_date) -> List[MonthlyKline]`

获取指定日期范围内的股票月线行情（按日期升序）。

| 参数 | 类型 | 说明 |
|------|------|------|
| `symbols` | `List[str]` | 股票代码列表 |
| `start_date` | `str` | 起始日期 |
| `end_date` | `str` | 结束日期 |

| 返回 | 说明 |
|------|------|
| `List[MonthlyKline]` | 月线行情列表 |

---

### `get_daily_close_prices(code, start_date, end_date) -> List[float]`

获取指定股票的日线收盘价列表（按日期升序）。

| 参数 | 类型 | 说明 |
|------|------|------|
| `code` | `str` | 股票代码 |
| `start_date` | `str` | 起始日期 |
| `end_date` | `str` | 结束日期 |

```python
prices = api.get_daily_close_prices('600519.SH', '2026-01-01', '2026-03-01')
```

---

### `get_daily_open_prices(code, start_date, end_date) -> List[float]`

获取指定股票的日线开盘价列表。

---

### `get_daily_high_prices(code, start_date, end_date) -> List[float]`

获取指定股票的日线最高价列表。

---

### `get_daily_low_prices(code, start_date, end_date) -> List[float]`

获取指定股票的日线最低价列表。

---

### `get_daily_volumes(code, start_date, end_date) -> List[float]`

获取指定股票的日线成交量列表。

---

### `get_daily_pct_chg(code, start_date, end_date) -> List[float]`

获取指定股票的日线涨跌幅列表（单位：%）。

---

### `get_tick_data(code, date) -> Optional[Dict]`

获取指定日期的 Tick 级数据（模拟级）。

| 参数 | 类型 | 说明 |
|------|------|------|
| `code` | `str` | 股票代码 |
| `date` | `str` | 日期，格式 `YYYY-MM-DD` |

| 返回字段 | 说明 |
|----------|------|
| `time` | 时间 |
| `open` | 开盘价 |
| `high` | 最高价 |
| `low` | 最低价 |
| `close` | 收盘价 |
| `volume` | 成交量 |
| `amount` | 成交额 |

```python
tick = api.get_tick_data('600519.SH', '2026-03-01')
```

---

### `get_realtime_bar(code, date) -> Dict`

获取实时 Bar 数据（同 `get_tick_data`，用于实盘级接口）。

---

## 技术指标（带缓存）

### `get_sma(code, date, period=20) -> Optional[float]`

获取简单移动平均 SMA。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `code` | `str` | — | 股票代码 |
| `date` | `str` | — | 计算日期，格式 `YYYY-MM-DD` |
| `period` | `int` | `20` | 周期 |

```python
sma = api.get_sma('600519.SH', '2026-03-01', 20)
```

---

### `get_ema(code, date, period=12) -> Optional[float]`

获取指数移动平均 EMA。

---

### `get_rsi(code, date, period=14) -> Optional[float]`

获取相对强弱指标 RSI（值域 0~100）。

```python
rsi = api.get_rsi('600519.SH', '2026-03-01', 14)
if rsi and rsi < 30:
    print('超卖')
```

---

### `get_bollinger_bands(code, date, period=20, std_dev=2) -> Optional[Dict]`

获取布林带指标。

| 返回字段 | 说明 |
|----------|------|
| `upper` | 上轨 |
| `middle` | 中轨 |
| `lower` | 下轨 |

```python
bb = api.get_bollinger_bands('600519.SH', '2026-03-01')
if bb and close > bb['upper']:
    print('突破上轨')
```

---

### `get_macd(code, date, fast=12, slow=26, signal=9) -> Optional[Dict]`

获取 MACD 指标。

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

```python
macd = api.get_macd('600519.SH', '2026-03-01')
if macd and macd['histogram'] > 0:
    print('多头')
```

---

### `get_atr(code, date, period=14) -> Optional[float]`

获取平均真实波幅 ATR。

---

## 性能指标

### `get_max_drawdown(equity_curve) -> tuple`

计算最大回撤。

| 返回 | 说明 |
|------|------|
| `(最大回撤比例, 最高点索引, 最低点索引)` | 元组 |

```python
dd, peak_idx, drawdown_idx = api.get_max_drawdown([1000000, 1100000, 950000])
print(f'最大回撤: {dd:.2%}')
```

---

### `get_max_drawdown_pct(equity_curve) -> float`

获取最大回撤百分比（如 `0.15` 表示 15%）。

---

### `get_annualized_return(total_return, days) -> float`

计算年化收益率。

| 参数 | 类型 | 说明 |
|------|------|------|
| `total_return` | `float` | 总收益率，如 `0.15` 表示 15% |
| `days` | `int` | 交易天数 |

---

### `get_total_return(initial_value, final_value) -> float`

计算总收益率。

---

### `get_sharpe_ratio(equity_curve, risk_free_rate=0.03) -> float`

计算夏普比率。

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `risk_free_rate` | `0.03` | 无风险利率（年化） |

```python
sharpe = api.get_sharpe_ratio([1000000, 1050000, 1020000])
```

---

### `get_win_rate(trades) -> float`

计算胜率（0~100）。

| 参数 | 说明 |
|------|------|
| `trades` | 交易记录列表，每条含 `{'profit': 盈亏金额}` |

```python
trades = [{'profit': 1000}, {'profit': -500}, {'profit': 800}]
win_rate = api.get_win_rate(trades)
```

---

### `get_profit_loss_ratio(trades) -> float`

计算盈亏比（平均盈利 / 平均亏损）。

---

### `get_calmar_ratio(equity_curve, days) -> float`

计算卡尔玛比率（年化收益 / 最大回撤）。

---

### `get_volatility(equity_curve) -> float`

计算年化波动率。

---

### `get_trade_stats(trades) -> Dict`

获取交易统计信息。

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

### `calculate_metrics(equity_curve, trades, initial_cash, days) -> Dict`

生成完整回测报告。

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

```python
equity = [1000000, 1050000, 1020000]
trades = [{'profit': 5000}, {'profit': -3000}]
report = api.calculate_metrics(equity, trades, 1000000, 30)
print(f"收益率: {report['total_return_pct']:.2f}%")
print(f"夏普比率: {report['sharpe_ratio']:.2f}")
```

---

## 回测工具

### `simulate_trade(action, price, quantity, fee_rate=0.0003) -> Dict`

模拟单笔交易，计算成本和手续费。

| 参数 | 说明 |
|------|------|
| `action` | `'BUY'` 或 `'SELL'` |
| `price` | 成交价格 |
| `quantity` | 成交数量 |
| `fee_rate` | 手续费率，默认万三 |

| 返回字段 | 说明 |
|----------|------|
| `cost` | 成本 |
| `fee` | 手续费 |
| `net_proceeds` | 净收款（卖出时） |

---

### `calculate_trade_cost(action, price, quantity, fee_rate=0.0003, slippage=0.0) -> float`

计算交易成本（含手续费和滑点）。

---

### `create_position(code, shares, price, date) -> Position`

创建持仓对象。

```python
pos = api.create_position('600519.SH', 100, 1800.0, '2026-01-01')
```

---

### `get_position_value(position, current_price) -> float`

计算持仓市值。

---

### `get_position_profit(position, current_price) -> tuple`

计算持仓盈亏。

| 返回 | 说明 |
|------|------|
| `(盈亏金额, 盈亏比例)` | 元组 |

```python
profit, pct = api.get_position_profit(position, 2000.0)
print(f"盈利: {profit}, 比例: {pct:.2%}")
```

---

### `calculate_portfolio_value(cash, positions, prices) -> float`

计算组合总价值（现金 + 持仓市值）。

```python
value = api.calculate_portfolio_value(500000, positions, current_prices)
```

---

### `get_portfolio_positions(positions) -> List[Dict]`

获取组合持仓详情列表。

---

### `build_equity_curve(daily_values) -> List[float]`

从每日资产构建权益曲线。

| 参数 | 说明 |
|------|------|
| `daily_values` | `[(日期, 资产), ...]` 按日期升序 |

```python
values = [('2026-01-01', 1000000), ('2026-01-02', 1005000)]
curve = api.build_equity_curve(values)
```

---

### `calculate_daily_returns(equity_curve) -> List[float]`

计算日收益率序列。

---

### `should_buy(current_price, ma_short, ma_long, rsi=50, rsi_oversold=30) -> bool`

买入信号判断（MA 金叉 + RSI 超卖）。

```python
if api.should_buy(close, ma5, ma20, rsi, 30):
    print('买入信号')
```

---

### `should_sell(current_price, ma_short, ma_long, rsi=50, rsi_overbought=70) -> bool`

卖出信号判断（MA 死叉或 RSI 超买）。

```python
if api.should_sell(close, ma5, ma20, rsi, 70):
    print('卖出信号')
```

---

### `calculate_drawdown(equity_curve) -> List[float]`

计算回撤序列。

```python
drawdowns = api.calculate_drawdown([1000000, 1100000, 950000])
```

---

### `buy(cash, positions, code, price, quantity, date, fee_rate=0.0003) -> Tuple`

买入股票（纯函数，无副作用）。

| 返回 | 说明 |
|------|------|
| `(更新后的现金, 更新后的持仓字典, TradeResult)` | 元组 |

```python
new_cash, new_positions, result = api.buy(1000000, {}, '600519.SH', 1800.0, 100, '2026-01-01')
if result.success:
    print(f'买入成功，成本: {result.cost}')
```

---

### `sell(cash, positions, code, price, quantity, fee_rate=0.0003) -> Tuple`

卖出股票（纯函数，无副作用）。

```python
new_cash, new_positions, result = api.sell(900000, positions, '600519.SH', 1900.0, 100)
if result.success:
    print(f'卖出成功，净收款: {result.net_proceeds}')
```

---

## 回测引擎控制

### `init_backtest(initial_cash=1000000.0, fee_rate=0.0003) -> Dict`

初始化回测环境，返回环境字典。

| 返回字段 | 说明 |
|----------|------|
| `initial_cash` | 初始资金 |
| `fee_rate` | 手续费率 |
| `cash` | 当前现金 |
| `positions` | 持仓字典 |
| `orders` | 订单列表 |
| `trades` | 交易记录 |
| `equity_curve` | 权益曲线 |

```python
env = api.init_backtest(1000000, 0.0003)
```

---

### `execute_buy(env, code, price, quantity, date) -> Dict`

执行买入操作，自动更新 `env` 中的现金、持仓和交易记录。

| 返回字段 | 说明 |
|----------|------|
| `success` | 是否成功 |
| `cost` | 成本 |
| `fee` | 手续费 |
| `reason` | 失败原因（失败时） |

---

### `execute_sell(env, code, price, quantity) -> Dict`

执行卖出操作，自动更新 `env`。

| 返回字段 | 说明 |
|----------|------|
| `success` | 是否成功 |
| `net_proceeds` | 净收款 |
| `fee` | 手续费 |
| `reason` | 失败原因（失败时） |

---

### `get_equity(env, current_prices) -> float`

获取当前总权益（现金 + 持仓市值）。

---

### `record_equity(env, date, current_prices) -> None`

将当日权益追加记录到 `env['equity_curve']`。

---

### `open_position(code, price, quantity, date) -> Position`

开仓（买入建立多头持仓）。

```python
pos = api.open_position('600519.SH', 1800.0, 100, '2026-01-01')
```

---

### `close_position(position, price, date) -> Dict`

平仓（卖出结束多头持仓）。

| 返回字段 | 说明 |
|----------|------|
| `profit` | 盈亏金额 |
| `profit_pct` | 盈亏比例 |
| `hold_days` | 持有天数 |

```python
result = api.close_position(position, 1900.0, '2026-01-15')
print(f"盈利: {result['profit']}")
```

---

### `update_position_price(position, current_price) -> None`

更新持仓的当前价格（用于市价计算）。

---

### `create_order(code, action, price, quantity) -> Dict`

创建订单（本地模拟，非真实下单）。

| 返回字段 | 说明 |
|----------|------|
| `order_id` | 订单 ID |
| `status` | 状态（`PENDING`） |
| `create_time` | 创建时间 |

---

### `cancel_order(order) -> bool`

取消订单（仅 `PENDING` 状态可取消）。

---

### `get_order_status(order) -> str`

获取订单状态：`PENDING` / `FILLED` / `CANCELLED` / `REJECTED`。

---

## 策略辅助函数

### `get_price_change_rate(code, date, days=3) -> Optional[float]`

计算近 N 日平均涨幅（%）。

```python
avg_change = api.get_price_change_rate('600519.SH', '2026-03-01', 3)
```

---

### `get_top_performers(codes, date, days=3, top_n=3) -> List[tuple]`

获取近 N 日涨幅最高的股票，返回 `[(code, avg_pct), ...]` 按涨幅降序。

```python
top_stocks = api.get_top_performers(codes, '2026-03-01', 3, 3)
```

---

### `get_price_at_date(code, date) -> Optional[float]`

获取指定日期的收盘价，无数据返回 `None`。

```python
price = api.get_price_at_date('600519.SH', '2026-03-01')
```

---

### `get_prices_at_dates(code, dates) -> List[Optional[float]]`

获取多个日期的收盘价列表（按日期升序）。

```python
prices = api.get_prices_at_dates('600519.SH', ['2026-01-01', '2026-01-02'])
```

---

## 数据库维护

### `init_databases() -> None`

初始化所有数据库（指标缓存库等）。

---

### `clear_indicator_cache(code=None) -> None`

清除技术指标缓存。

| 参数 | 说明 |
|------|------|
| `code` | 股票代码，`None` 表示清除所有缓存 |

```python
api.clear_indicator_cache('600519.SH')  # 清除指定股票
api.clear_indicator_cache()             # 清除所有
```
