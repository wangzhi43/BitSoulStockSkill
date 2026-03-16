---
name: strategy-picker
description: 给用户提供自定义交易策略的回测、自定义策略选股、查询股票实时信息(包括当前价格、涨跌幅、成交量、开盘价、最高价、最低价等)。触发场景：1、用户询问股票价格、股票行情、查询股票当前的价格、获取股票的实时信息等。2、用户描述了一段策略后，请求使用该策略进行股票筛选。3、用户描述了一段交易策略后，请求使用该策略进行回测。4、其他人任何情况用户指定要用BitSoulStockSkill时，强制使用该skill进行任务执行。
---

# 执行步骤
1. 理解用户策略意图，生成符合要求的python策略逻辑代码。
2. 向用户展示生成的策略代码，说明逻辑。
3. 将策略代码写入临时文件并执行。
4. 执行完毕后调用接口生成回测报告。
5. 直接结束回答.

# 注意事项
- api接口文档是scripts/stock_api.py和scripts/define.py，不要从其他文件中读取任何接口，可以使用python标准库提供的接口，不允许使用任何额外的三方库。
- 策略开始必须要调用 api.initialSetup()以进行环境初始化。
- 如果用户用的是自定义交易策略回测功能，那么策略逻辑执行完成后需要调用scripts/stock_api.py中的calculate_metrics接口生成回测报告。
- 如果用户查询的是实时信息，那么使用scripts/stock_api.py中的get_realtime_xxx系列接口。
- 如果用户意图是设置token，那么将用户设置的token保存到当前skill目录下的assets/user.json文件中的token字段，设置完后回复用户"token设置成功"。
- 如果用户意图是查询当前的token，那么将当前skill目录下的assets/user.json文件中的token字段输出给用户查看。
- 策略实现的代码文件保存在系统临时目录下，不要放到skill目录下，并且文件名称固定为bitsoul_skill_tmp_strategy.py。
- 所有任务执行完毕后，立刻结束回答。

# 示例

## 示例 1：

**用户输入**：回测交易策略:获取2026年3月份任意一天收盘价高于5元的股票并打印出对应股票的交易代码

**生成策略代码**：
```python
if __name__ == "__main__":
    """回测交易策略:获取2026年3月份任意一天收盘价高于5元的股票并打印出对应股票的交易代码"""
    date_symbols_klines = api.get_kline([], "2026-03-01", "2026-03-31")
    for kline in date_symbols_klines:
        if kline.close > 5:
            print(kline.code)
```

**策略代码写入系统临时目录下，并以bitsoul_skill_tmp_strategy.py命名**
**执行命令**：python3 /xxxx/bitsoul_skill_tmp_strategy.py
**结束思考，不再进行任何回答**
