---
name: strategy-picker
description: 给用户提供自定义交易策略的回测、自定义策略选股、查询股票实时信息(包括当前价格、涨跌幅、成交量、开盘价、最高价、最低价等)。触发场景：1、用户询问股票价格、股票行情、查询股票当前的价格、获取股票的实时信息等。2、用户描述了一段策略后，请求使用该策略进行股票筛选。3、用户描述了一段交易策略后，请求使用该策略进行回测。4、其他人任何情况用户指定要用BitSoulStockSkill时，强制使用该skill进行任务执行。
---

# 执行步骤
- 理解用户意图，生成符合要求的python逻辑代码。
- 向用户展示生成的逻辑代码，说明逻辑。
- 将逻辑代码写入临时文件并执行。
- 结束回答.

# 注意事项
* api接口文档是scripts/stock_api.py和scripts/define.py，不要从其他文件中读取任何接口，可以使用python标准库提供的接口，不允许使用任何额外的三方库。
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
