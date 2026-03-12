---
name: strategy-picker
description: 当用户想用自定义交易策略看回测效果时激活。用户用自然语言描述交易策略，skill 将其转换为 Python 策略代码并调用 strategy_runner.py 执行。示例触发语句："回测交易策略:买入近三日平均日涨幅最高的前3只股票,每只股票固定买入100股,当资金不够时,不再买入,当股价高于买入时的10%时,卖出对应股票。
argument-hint: <策略描述或内置策略名>
---

# 自定义策略选股 Skill

## 执行步骤
**1**：理解用户策略意图，生成符合以下规范的 Python 策略函数,StockApi来自于scripts/stock_api.py文件：

```python
def strategy(api:StockApi):
    """策略描述"""
    # 使用 api.xxx() 调用基础数据接口
    ...
```
**2**：向用户展示生成的策略代码，说明逻辑。

**3**：将策略代码写入临时文件，然后调用scripts/strategy_runner.py，并将策略文件路径用 `--strategy-file` 传入
```
python3 scripts/strategy_runner.py --strategy-file "策略实现文件路径"
```
**4**：等待脚本执行完毕，直接结束回答.

---

## 注意事项
- 策略实现中，函数签名必须为 `def strategy(api:StockApi):`
- 策略实现的代码文件保存在系统临时目录下，不要放到skill目录下，并且文件名称固定为bitsoul_skill_tmp_strategy.py
- 策略实现时所需的股票操作相关的接口可从 scripts/stock_api.py 和 scripts/define.py 获取，scripts/stock_api.py文件中只使用StockApi类提供的接口。
- 策略实现中只能使用 `api.xxx()` 访问股票/行情等数据，不得访问外部网络，不得访问任何其他skill
- 允许使用 Python 内置函数（`all`, `any`, `sum`, `min`, `max` 等），不允许使用任何三方库，如有需要，请直接报错"策略引用外部依赖，请调整描述"然后立即终止
- 策略逻辑执行完成后后立刻结束回答

## 示例

### 示例 1：

**用户输入**：回测交易策略:获取2026年3月份任意一天收盘价高于5元的股票并打印出对应股票的交易代码

**生成策略代码**：
```python
def strategy(api:StockApi) -> bool:
    """回测交易策略:获取2026年3月份任意一天收盘价高于5元的股票并打印出对应股票的交易代码"""
    date_symbols_klines = api.get_kline([], "2026-03-01", "2026-03-31")
    for kline in date_symbols_klines:
        if kline.close > 5:
            print(kline.code)
```

**策略代码写入系统临时目录下，并以bitsoul_skill_tmp_strategy.py命名：

**执行命令**：
```
python3 scripts/strategy_runner.py --strategy-file /xxxx/bitsoul_skill_tmp_strategy.py
```

**结束思考，不再进行任何回答**
---
