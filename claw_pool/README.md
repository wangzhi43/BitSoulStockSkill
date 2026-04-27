# Claw Pool 模拟交易系统

## 概述

claw_pool 是一个大规模模拟交易系统，包含1000个模拟账户，每个账户使用随机配置的MOE（混合专家）权重进行股票交易模拟。

### 主要功能

- 生成1000个随机MOE权重配置
- 模拟指定日期范围的股票交易
- 统计账户收益、最大回撤、夏普比率等指标
- 生成每日排行榜（CSV和JSON格式）
- 导出排行榜前N名账户的MOE配置

---

## 脚本说明

### 1. claw_pool_sim_runner.py - 运行模拟

用于初始化账户并运行模拟交易。

#### 当前回测口径

- 选股信号使用前一交易日数据，避免使用当日收盘价做当日交易产生未来函数
- 实际成交价使用交易日开盘价，交易流水会额外记录 `信号日期` 与 `成交价类型`
- 买入数量按 A 股规则约束为 `100` 股整数倍
- 当天无成交量或无开盘价时，不允许成交
- 对日线可客观识别的一字涨停 / 一字跌停做成交拦截
- 持仓估值使用“当日及之前最近一条日线收盘价”，避免停牌或局部缺数时把持仓错误估成 `0`
- 动量评分在近 5 日比较时叠加 `adj_factor`，尽量降低分红送股导致的价格突变干扰

#### 基本用法

```bash
# 生成随机权重，运行完整模拟
python claw_pool\claw_pool_sim_runner.py --start 2026-03-16 --end 2026-03-20
```

#### 禁用随机权重生成

当需要使用已有的MOE配置文件时，使用此选项：

```bash
python claw_pool\claw_pool_sim_runner.py --start 2026-03-16 --end 2026-03-20 --no-generate-weights --weights-dir .\claw_pool
```

#### 指定账户数量

```bash
python claw_pool\claw_pool_sim_runner.py --start 2026-03-16 --end 2026-03-20 --accounts 500
```

#### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--start` | 开始日期 (YYYY-MM-DD) | 必填 |
| `--end` | 结束日期 (YYYY-MM-DD) | 必填 |
| `--no-generate-weights` | 禁用随机权重生成 | 生成新权重 |
| `--weights-dir` | 指定权重文件夹路径 | claw_pool目录 |
| `--accounts` | 账户数量 | 1000 |
| `--keep-accounts` | 保留权重的账户ID列表(JSON格式) | 无 |

#### 输出文件

运行后在 `claw_pool\ranking` 目录下创建新文件夹（如 `ranking_1774778810`），包含：

- `ranking_YYYY-MM-DD.csv` - CSV格式排行榜（UTF-8编码）
- `ranking_YYYY-MM-DD.json` - JSON格式完整数据
- `trades/` - 前100名账户的详细交易记录目录
  - `account_XXXX_trades.csv` - 单个账户的每日交易流水（含 `信号日期`、`成交价类型`）

#### 审计脚本

可用 `audit_sim_runner.py` 对单次回测结果做快速复核：

```powershell
python claw_pool\audit_sim_runner.py --ranking-dir d:\codebase\BitSoulStockSkill\claw_pool\ranking\ranking_1776390103
```

当前审计会检查：

- 买入股数是否为 `100` 股整数倍
- 成交价是否等于当日开盘价
- 是否误买入一字涨停 / 误卖出一字跌停
- 数据库中是否存在超过 `30%` 的单日价格跳变样本

#### 涨跌停表回填

当前分发的 `data_1.0.bin` / `data_1.0 (7).bin` 中未包含：

- `stock_limit`
- `daily_limit_list`
- `daily_bomb_list`

如果本地数据库中这三张表为空，可先执行回填脚本生成“标准表结构下的推导版数据”：

```powershell
python claw_pool\backfill_limit_tables.py --truncate
```

说明：

- 回测器会优先读取 `stock_limit` 表中的涨跌停价
- 如果正式表缺失，则回退到代码启发式推断
- 回填脚本基于 `daily_kline` 和 `stock_basic` 推导，只适用于提升日频回测客观性，不等同于交易所级精准盘口

---

### 2. export_top_configs.py - 导出MOE配置

用于将排行榜前N名账户的MOE配置文件导出到指定目录。

#### 基本用法

```bash
python claw_pool\export_top_configs.py --date 2026-03-17 --top 50 --output .\top_configs
```

#### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--date` | 排行榜日期 (YYYY-MM-DD) | 必填 |
| `--top` | 导出前N个账户 | 50 |
| `--output` | 输出文件夹路径 | ./export_top_configs |
| `--ranking-dir` | 指定排行榜目录 | 自动查找最新目录 |

#### 输出内容

导出的目录结构：

```
top_configs/
├── manifest.csv              # 账户清单（包含收益数据）
├── account_0001/
│   └── moe_weights.json      # MOE权重配置
├── account_0002/
│   └── moe_weights.json
└── ...
```

#### manifest.csv 格式

```csv
account_id,total_return_pct,daily_return_pct,max_drawdown,sharpe_ratio
581,3.26,3.32,0.06,0
844,2.89,2.95,0.09,0
...
```

---

## 排行榜字段说明

CSV文件包含以下字段（JSON文件包含更详细的原始数值）：

| 字段 | 说明 |
|------|------|
| 总排名 | 在所有日期中的总收益率排名 |
| 龙虾id | 账户编号（即账户ID） |
| 持仓市值(万) | 持仓股票总市值，单位为万，保留一位小数 |
| 账户总额(万) | 现金+持仓市值，单位为万，保留一位小数 |
| 总收益率(%) | 从开始到现在的累计收益率 |
| 当日收益率(%) | 当日收益率 |
| 历史最大回撤(%) | 累计最大回撤 |
| 夏普比率 | 累计夏普比率 |
| 持仓股票 | 股票名称和股数 |

---

## 持仓数量说明

模拟系统中持仓数量会在4-10只之间随机变化，每个账户在初始化时随机分配一个最大持仓数量。

### 示例分布

```
4只: ~147个账户
5只: ~132个账户
6只: ~141个账户
7只: ~151个账户
8只: ~154个账户
9只: ~144个账户
10只: ~131个账户
```

---

## 工作流程示例

### 完整模拟流程

1. **运行模拟生成排行榜**

   ```bash
   python claw_pool\claw_pool_sim_runner.py --start 2026-03-16 --end 2026-03-20
   ```

2. **查看排行榜（3月20日）**

   ```bash
   python claw_pool\query_ranking.py 2026-03-16 2026-03-20
   ```

3. **导出前50名账户配置**

   ```bash
   python claw_pool\export_top_configs.py --date 2026-03-20 --top 50 --output .\top50_configs
   ```

4. **使用导出的配置重新模拟**

   ```bash
   python claw_pool\claw_pool_sim_runner.py --start 2026-03-21 --end 2026-03-21 --no-generate-weights --weights-dir .\top50_configs --accounts 50
   ```

---

## 查询排行榜

使用 `query_ranking.py` 查询指定日期范围的排行榜：

```bash
python claw_pool\query_ranking.py 2026-03-16 2026-03-20
```

自动查找最新的ranking目录并显示每日排行榜前10名。

---

## 绘制龙虾收益率曲线

使用 `plot_lobster_curve.py` 绘制特定账户的累计收益率曲线图（采用现代前端设计风格）：

#### 基本用法

```bash
# 为 710 号龙虾绘制收益率曲线
python claw_pool\plot_lobster_curve.py --dir claw_pool\ranking\ranking_1775788853 --ids 710
```

#### 进阶用法

支持同时为多个龙虾生成图表，并可指定日期范围：

```bash
# 为 710, 800, 221 号龙虾分别绘制收益率曲线，并限制日期在 3.16 - 3.31 之间
python claw_pool\plot_lobster_curve.py --dir claw_pool\ranking\ranking_1775788853 --ids 710 800 221 --start 2026-03-16 --end 2026-03-31
```

生成的图表会以 `lobster_ID_return_curve.png` 的形式直接保存在 `--dir` 指定的排行榜文件夹中。

---

## 文件位置

- 脚本目录: `d:\codebase\BitSoulStockSkill\claw_pool\`
- 账户数据: `d:\codebase\BitSoulStockSkill\claw_pool\account\account_XXXX\`
- 排名数据: `d:\codebase\BitSoulStockSkill\claw_pool\ranking\ranking_XXXXXX\`
- 数据库: `C:\Users\admin\AppData\Local\Temp\BitSoulStockSkill\data.db`

### 目录结构

```
claw_pool/
├── account/                    # 1000个账户目录
│   ├── account_0001/
│   │   └── moe_weights.json
│   ├── account_0002/
│   │   └── moe_weights.json
│   └── ...
├── ranking/                     # 排名数据目录
│   ├── ranking_XXXXXXXX/
│   │   ├── ranking_2026-03-16.csv
│   │   ├── ranking_2026-03-16.json
│   │   ├── trades/              # 前100名交易记录
│   │   │   └── account_XXXX_trades.csv
│   │   └── ...
│   └── ...
├── claw_pool_sim_runner.py      # 模拟运行脚本
├── export_top_configs.py        # 导出MOE配置
├── query_ranking.py             # 查询排行榜
└── README.md
```
