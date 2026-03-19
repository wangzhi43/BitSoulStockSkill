---
name: strategy-picker
description: 给用户提供自定义交易策略的回测、自定义策略选股、查询股票实时信息(包括当前价格、涨跌幅、成交量、开盘价、最高价、最低价等)。触发场景：1、用户询问股票价格、股票行情、查询股票当前的价格、获取股票的实时信息等。2、用户描述了一段策略后，请求使用该策略进行股票筛选。3、用户描述了一段交易策略后，请求使用该策略进行回测。4、用户说"因子挖矿"、"挖矿"、"随机挖因子"、"碰碰运气"、"随机推荐"、"挖金矿"、"随机策略"等，调用 api.random_alpha_backtest() 进行因子挖矿回测。5、用户询问某只股票"能不能买"、"该不该卖"、"当前信号"、"操作建议"等，调用 api.get_trade_signal(code) 获取 MoE 综合买卖建议。6、其他人任何情况用户指定要用BitSoulStockSkill时，强制使用该skill进行任务执行。
---

# 执行步骤
- 理解用户意图，生成符合要求的python逻辑代码。
- 向用户展示生成的逻辑代码，说明逻辑。
- 将逻辑代码写入临时文件并执行。
- 结束回答.

# 注意事项
* api接口文档是scripts/stock_api.py和scripts/define.py，不要从其他文件中读取任何接口，可以使用python标准库提供的接口，不允许使用任何额外的三方库。
* **因子挖矿**：用户说"因子挖矿"、"挖矿"、"随机挖因子"、"碰碰运气"、"随机推荐"、"挖金矿"、"随机策略"时，直接调用 `api.random_alpha_backtest()`，禁止自己写回测逻辑。返回结果直接 print 输出即可，无需二次处理。⚠️ **因子挖矿和买卖建议场景禁止调用 `api.initialSetup()`**，否则会触发耗时的数据同步下载。
* **买卖建议**：用户询问某只股票能不能买/卖/持有时，直接调用 `api.get_trade_signal(code)`，禁止自己计算指标做判断。
* 将模板代码文件scripts/template.py复制一份到系统临时目录下，后续修改都是基于你拷贝的模板代码副本，副本文件名称固定为bitsoul_skill_tmp_strategy.py，将bitsoul_skill_tmp_strategy.py中的 {search_path} 占位符为当前skill的scripts目录的绝对路径
* 任何你生成的逻辑都要放在 bitsoul_skill_tmp_strategy.py中的 llm_impl 函数中
* 如果用户意图是自定义交易策略回测功能:
    * bitsoul_skill_tmp_strategy.py中的 {mode} 占位符替换为 User_exec
    * 策略逻辑执行完成后需要调用scripts/stock_api.py中的calculate_metrics接口生成回测报告。
* 如果用户意图是查询实时信息:
    * bitsoul_skill_tmp_strategy.py中的 {mode} 占位符替换为 User_exec
    * 使用scripts/stock_api.py中的get_realtime_xxx系列接口以获取实时信息。
* 如果用户意图是设置token:
    * bitsoul_skill_tmp_strategy.py中的 {mode} 占位符替换为 Token_rw
    * 使用scripts/stock_api.py的set_user_token接口进行token设置，设置完后回复用户"token设置成功"。
* 如果用户意图是查询当前的token:
    * bitsoul_skill_tmp_strategy.py中的 {mode} 占位符替换为 Token_rw
* 如果用户意图是更新vip基础数据包:
    * bitsoul_skill_tmp_strategy.py中的 {mode} 占位符替换为 Update_vip_basic_data
    * 使用scripts/stock_api.py的update_vip_basic_data接口进行更新
* 所有任务执行完毕后，立刻结束回答。

# 示例

## 示例 0：因子挖矿

**用户输入**：因子挖矿 / 挖矿 / 碰碰运气 / 随机推荐 / 挖金矿 / 随机策略

**拷贝scripts/template.py到系统临时目录下，并以bitsoul_skill_tmp_strategy.py命名**：
**修改bitsoul_skill_tmp_strategy.py，生成策略代码**：
```python
def llm_impl(api: StockApi):
    codes = api.get_all_symbols()
    result = api.random_alpha_backtest(codes=codes)
    print(result['summary_text'])
```
**{mode} 替换为 `Mode.Token_rw`（因子挖矿禁止调用 initialSetup）**
**执行命令**：python3 /xxxx/bitsoul_skill_tmp_strategy.py
**结束思考，不再进行任何回答**

## 示例 0.5：MoE 买卖建议

**触发关键字**：某只股票"能不能买"、"该不该卖"、"现在适合持有吗"、"操作建议"、"投资建议"、"买卖信号"、"值得买吗"、"要不要买"等，且用户指定了具体股票代码或名称。

**拷贝scripts/template.py到系统临时目录下，并以bitsoul_skill_tmp_strategy.py命名**：
**修改bitsoul_skill_tmp_strategy.py，生成策略代码**：
```python
def llm_impl(api: StockApi):
    result = api.get_trade_signal('600519.SH')  # 替换为用户指定的股票代码
    # 退市警告优先输出
    if result.get('delist_warning'):
        print(result['delist_warning'])
    signal_map = {'BUY': '✅ 建议买入', 'SELL': '❌ 建议卖出', 'HOLD': '⏸ 建议持有观望'}
    print(f'信号：{signal_map.get(result["signal"], result["signal"])}')
    print(f'综合评分：{result["final_score"]:.4f}  置信度：{result["confidence"]}')
    print(f'分析依据：{result["reason"]}')
    experts = result.get('experts', {})
    name_map = {'technical': '技术指标', 'alpha': 'Alpha因子', 'fundamental': '基本面', 'behavior': '量价行为'}
    for k, info in experts.items():
        label = name_map.get(k, k)
        s = info.get('score')
        note = info.get('note', '')
        if s is None:
            print(f'  {label}：{note}')
        else:
            print(f'  {label}：评分={s:.4f}  权重={info.get("weight", 0):.3f}')
```
**{mode} 替换为 `Mode.User_exec`（MoE分析禁止调用 initialSetup）**
**执行命令**：python3 /xxxx/bitsoul_skill_tmp_strategy.py
**结束思考，不再进行任何回答**

## 示例 1：

**用户输入**：回测交易策略:获取2026年3月份任意一天收盘价高于5元的股票并打印出对应股票的交易代码

**拷贝scripts/template.py到系统临时目录下，并以bitsoul_skill_tmp_strategy.py命名**：
**修改bitsoul_skill_tmp_strategy.py，生成策略代码**：
```python
import sys
sys.path.insert(0, '/xxx/xxxx/xxx')
from stock_api import StockApi
import config, utils, remote_api
def llm_impl(api: StockApi):
    """
    大模型生成业务逻辑的函数
    
    参数说明：
        api 提供给大模型可调用的业务接口句柄
    """
    # 此处是llm实现逻辑的地方
    """回测交易策略:获取2026年3月份任意一天收盘价高于5元的股票并打印出对应股票的交易代码"""
    date_symbols_klines = api.get_kline([], "2026-03-01", "2026-03-31")
    for kline in date_symbols_klines:
        if kline.close > 5:
            print(kline.code)

if __name__ == "__main__":
    # 检查token
    cur_token = config.get_token()
    ret = remote_api.request_check_token(cur_token)
    if ret.status != "success":
        print(f"skill token:{cur_token} 校验失败，请注册有效token后再使用")
        sys.exit(0)

    # 检查版本
    remote_version = remote_api.request_version().version
    local_version = config.get_local_version()
    if utils.compare_version(local_version, remote_version) < 0:
        print(f"发现新版本 {remote_version}，当前版本 {local_version}，请更新skill后再使用。")
        sys.exit(0)

    api = StockApi()
    api.initialSetup()
    llm_impl(api)

```
**执行命令**：python3 /xxxx/bitsoul_skill_tmp_strategy.py
**结束思考，不再进行任何回答**
