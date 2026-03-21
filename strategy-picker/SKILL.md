---
name: BitSoulStockSkill
description: 定位A股市场，向用户提供股票筛选策略，基于MOE混合因子专家模型的股票买卖点计算判断，个股风险判定，关键指标计算，数据回测，提供准确全面的股票价格与股票历史信息，板块信息与相关交易数据
version: 1.0.0
metadata:
  openclaw:
    emoji: "📈"
    homepage: https://www.aicodingyard.com
    requires:
      env:
        - BITSOUL_TOKEN
      bins:
        - python3
    optional:
      env:
        - BITSOUL_TOKEN_ENV_FILE
        - BITSOUL_CACHE_DIR
      pythonPackages:
        - pandas
        - numpy
        - requests
        - sqlalchemy
      network:
        - info.aicodingyard.com
        - https://finance.sina.com.cn/
    primaryEnv: BITSOUL_TOKEN
---


# Token 配置

本 skill 需要有效的 `BITSOUL_TOKEN` 才能使用功能

## 必需的环境变量

* `BITSOUL_TOKEN`：用户令牌，用于远程服务器权限验证

## 可选的环境变量

* `BITSOUL_TOKEN_ENV_FILE`：指向包含 `BITSOUL_TOKEN` 的 env 文件

## 配置方式

1. **方式一：直接设置环境变量**
   ```bash
   export BITSOUL_TOKEN="你的令牌"
   ```

2. **方式二：使用 env 文件**
   ```bash
   export BITSOUL_TOKEN_ENV_FILE="/path/to/token.env"
   ```
   其中 `token.env` 文件内容格式为：
   ```
   BITSOUL_TOKEN=你的令牌
   ```

**注意**：如果同时设置了环境变量和 env 文件，环境变量优先。

运行时描述：
- 从环境变量读取 `BITSOUL_TOKEN`
- 只有在显式提供 `BITSOUL_TOKEN_ENV_FILE` 时，才会从文件中读取 `BITSOUL_TOKEN`
- 从自然语言中自动选择更合适的股票接口
- 对“分析 / 估值 / 基本面 / 趋势 / 风险”等请求自动切到综合分析,需要moe因子计算，返回详细信息
- 对“交易观察 / 技术分析 / 均线 / 动量 / RSI / KDJ / 布林线 / MACD”等请求需要进行moe因子计算，同时需要调用calculate_metrics进行数据回测
- 返回结构化 JSON；查询场景优先给原始数据，分析场景给结论和支撑数据

## 安全与运行边界

- 技能所需环境变量已经在本文件 frontmatter 中显式声明
- 策略回测、因子挖矿、实时行情查询等功能会访问 `info.aicodingyard.com` 服务器
- 技能只读取声明过的 token 相关环境变量，以及显式指定的 env 文件路径
- 技能不会主动扫描其他本地凭证文件，也不会写入 token 缓存文件

## 安装

使用前先安装 Python 依赖：

```bash
pip install -r assets/requirements.txt
```
首次安装需要执行初始化操作，在设置好BITSOUL_TOKEN后，请运行scripts/data_fetcher.py

# 注意事项
* api接口文档主要参考 references/API_FOR_LLM.md 对应的代码文件是scripts/stock_api.py 和 scripts/define.py
* **凭证说明**：本skill需要用户Token用于数据访问权限验证。Token通过环境变量 `BITSOUL_TOKEN` 或 `BITSOUL_TOKEN_ENV_FILE` 传入。Token在数据访问时需要保持有效（请自行确保token未过期）。
* **缓存目录**：`BITSOUL_CACHE_DIR`，可选，用于指定缓存目录和数据存储路径。默认值为系统临时目录下的 `BitSoulStockSkill` 子目录
* **本地持久化文件**：
  * `{缓存目录}/data.db` - 股票行情、指标缓存
  * `{缓存目录}/logs/` - 日志目录
  * `assets/config.json` - 配置文件
* **因子挖矿**：用户说"因子挖矿"、"挖矿"、"随机挖因子"、"碰碰运气"、"随机推荐"、"挖金矿"、"随机策略"时，直接调用 `api.random_alpha_backtest()`，禁止自己写回测逻辑。返回结果调用 `print(result['summary_text'])` 输出，禁止自行整理摘要。
* **因子挖矿结束后**：在 `print(result['summary_text'])` 之后，用自然语言向用户逐一解释本次使用的每个因子是什么含义、在策略中起什么作用。解释来源是 `result['factor_descriptions']`，格式示例：`alpha022：高价量5日相关的5日变化 × 收盘波动率，用于衡量量价相关动量的衰减程度，在本次策略中作为选股因子使用。`
* **买卖建议**：用户询问某只股票"能不能买"、"该不该卖"、"现在适合持有吗"、"操作建议"、"投资建议"、"买卖信号"、"值得买吗"、"要不要买"等，且用户指定了具体股票时，直接调用 `api.get_trade_signal(code)`，禁止自己计算指标做判断。
* **股票显示格式**：任何场景下输出股票代码时，必须同时附上股票名称，使用 `api.get_symbol_basic_infomation(code).name` 获取，格式如 `600519.SH（贵州茅台）`，禁止只输出代码。




## 输出行为

- 面向用户的输出默认使用简体中文
- 查询类请求优先返回原始数据，再补详细解释
- 分析类请求默认返回结论、关键指标、风险提示与支撑摘要
- 交易观察优先输出趋势、量价、资金流、龙虎榜和技术指标信号
- 请求不明确时，先用中文追问一句，不要盲猜

## 示例请求

- `贵州茅台近一个月股价走势`
- `最近30天龙虎榜机构交易`
- `分析宁德时代的估值和成长性`
- `看看招商银行的基本面和趋势`
- `贵州茅台当前有哪些风险信号`
- `看看贵州茅台的交易观察`
- `看看贵州茅台的快档交易观察`
- `深度看看贵州茅台交易观察，带龙虎榜和机构席位`
- `分析宁德时代均线、RSI 和布林线`
- `贵州茅台技术分析`

## 参考资料

- 机器可读目录：`references/API_FOR_LLM.dm`

