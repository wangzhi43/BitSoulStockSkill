---
name: strategy-picker
description: 当用户想用自定义交易策略看回测效果时激活。用户用自然语言描述交易策略，skill 将其转换为 Python 策略代码并调用 strategy_runner.py 执行。示例触发语句："回测交易策略:买入近三日平均日涨幅最高的前3只股票,每只股票固定买入100股,当资金不够时,不再买入,当股价高于买入时的10%时,卖出对应股票。
argument-hint: <策略描述或内置策略名>
---

# 自定义策略选股 Skill

## 执行步骤

当用户触发此 skill 时：

### 情况一：用户要求运行内置策略

直接调用 runner，无需生成代码：
```
python3 scripts/strategy_runner.py --builtin <策略名>
```

### 情况二：用户描述自定义策略

**Step 1**：理解用户策略意图，生成符合以下规范的 Python 策略函数：

```python
def strategy(api):
    """策略描述"""
    # 使用 api.xxx() 调用基础数据接口
    ...
```

**Step 2**：向用户展示生成的策略代码，说明逻辑。

**Step 3**：将策略代码写入临时文件后用 `--strategy-file` 传入
```
python3 scripts/strategy_runner.py --strategy-file "策略函数代码文件路径"
```

**Step 4**：等待脚本执行完毕，直接结束回答

---

## 策略代码规范
- 函数签名必须为 `def strategy(api):`
- 只能使用 `api.xxx()` 访问股票数据，不得访问外部网络
- 允许使用 Python 内置函数（`all`, `any`, `sum`, `min`, `max` 等），不允许使用任何三方库，如有需要，请直接报错"策略引用外部依赖，请调整描述"然后立即终止

---

## 注意事项
- 策略实现时所需的股票操作相关的接口可从 scripts/stock_api.py 和 scripts/define.py 获取，其他文件不要扫描和读取
- 策略实现文件保存到系统临时目录下，不要放到skill目录下
- 执行完脚本后立刻结束回答, 不要进行任何推测，不要再进行任何回答
---

## 示例

### 示例 1：连续三天涨幅超 5%

**用户输入**：帮我筛选连续三天股价上涨超5%的股票

**生成策略代码**：
```python
def strategy(symbol: str, api) -> bool:
    """连续3天涨幅均超过5%"""
    changes = api.get_price_change_pct_list(symbol, 3)
    return all(chg > 5.0 for chg in changes)
```

**策略代码写入文件**：xxxx.py

**执行命令**：
```
python3 scripts/strategy_runner.py --strategy-file xxxx.py
```

---

### 示例 2：过去三年净利润增速 > 20%

**用户输入**：找过去三年净利润增速大于20%的股票

**生成策略代码**：
```python
def strategy(symbol: str):
    """过去3年净利润复合增长率 > 20%"""
    growth = api.get_net_profit_growth_rate(symbol, years=3)
    return growth > 20.0
```

---

### 示例 3：组合条件策略

**用户输入**：低估值高成长，PE < 25 且近三年利润增速 > 15% 且 ROE > 12%

**生成策略代码**：
```python
def strategy(api):
    """低估值高成长：PE<25，近3年利润增速>15%，ROE>12%"""
    pe = api.get_pe(symbol)
    if pe is None or pe >= 25:
        return False
    profit_growth = api.get_net_profit_growth_rate(symbol, years=3)
    roe = api.get_roe(symbol)
    return profit_growth > 15.0 and roe > 12.0
```
