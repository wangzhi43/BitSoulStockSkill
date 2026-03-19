# 🐉 BitSoulStockSkill

<img src="http://installskill.aicodingyard.com/BitSoulLogo.jpg" width="120" alt="BitSoulLogo" align="right" />

> 面向普通股民 / 金融爱好者 / 量化入门选手的 A股股票分析 Skill，赋能 AI Agent 成为你最好的财富助理和赚钱搭子

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)
[![Python 3.6+](https://img.shields.io/badge/Python-3.6+-green.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## ✨ 简介

BitSoulStockSkill 是面向 A股市场的股票分析 all-in-one 综合性 Skill，主要具备以下特色：

### 📊 1. 免费历史数据服务

自带完全免费的 A股历史数据服务，数据准确稳定，有专人维护，每周稳定更新。

| 数据类型 | 说明 |
| :--- | :--- |
| **历史行情** | 日线、周线、月线数据 |
| **基本面指标** | PE、PB、PS、股息、总市值等 |
| **财务数据** | EPS、营收、利润等 |
| **板块数据** | 板块资金流、涨跌幅数据 |
| **龙虎榜** | 每日龙虎榜数据 |
| **指数数据** | 主要指数行情 |

> 📌 **使用方法**：前往官网 [注册](https://www.aicodingyard.com/) 并生成 Token，即可获得过去半年的历史数据。
> 
> 💎 如需获取过去 10 年的历史数据，并按天更新即时数据，可前往官网注册 VIP 服务。

### 📈 2. 内置上百种量化指标

| 指标类型 | 包含内容 |
| :--- | :--- |
| **技术指标** | 移动平均线、RSI、布林带、MACD、K线图等 |
| **基本面指标** | 市盈率、市净率、股息率、总市值等 |
| **交易指标** | 量比、量价关系、量能关系等 |
| **自定义因子** | 支持用户添加个性化技术指标 |

### 🧠 3. 混合专家系统 (MoE)

基于因子层面的混合专家系统打造了一套针对**选股**、**买入/卖出点分析**、**一揽子交易**等具体问题的分析框架，结合 AI Agent 与大语言模型的推理能力，向用户提供简单易懂的投资建议。

- 🎯 **个性化权重更新**：基于用户与大模型的历史对话，沉淀出符合用户风险偏好的权重分布
- 🔄 **权重图谱共享**：官方定期分享高收益低回撤的策略权重方案，支持一键导入
- 📋 **策略回顾功能**：基于历史信息的因子策略回顾（规划中）

### 🔬 4. 完善的回测框架

高自由度的配置选项，结合内置的大量免费数据，支持用户自定义复杂数据回测逻辑。

---

## 📥 快速安装

### 方式一：龙的一句话安装

根据 [安装描述](http://installskill.aicodingyard.com/stockskill_install.txt) 文件，帮你安装 Skill：

```
根据 http://installskill.aicodingyard.com/stockskill_install.txt 这个描述，帮我安装 skill，我的 token 是：xxxxxx
```

### 方式二：GitHub 安装

```bash
# 1. 在本地 workspace/skills 目录下克隆仓库
git clone https://github.com/BitSoulTech/BitSoulStockSkill.git

# 2. 进入项目目录
cd BitSoulStockSkill

# 3. 安装依赖
pip install -r requirements.txt
```

### 方式三：ClawHub 安装

前往 [ClawHub](https://clawhub.com/) 下载 Skill 安装包。

---

## 📁 项目结构

```
BitSoulStockSkill/
├── strategy-picker/
│   └── scripts/
│       ├── data_fetcher.py      # 数据获取与本地 SQLite 持久化
│       ├── stock_crawler.py     # 多数据源实时行情爬虫
│       ├── define.py            # 数据类型定义
│       ├── remote_api.py        # 远程 API 接口封装
│       ├── db_engine.py         # 数据库引擎管理
│       ├── utils.py             # 工具函数
│       └── logger.py            # 日志模块
├── API_FOR_LLM.md               # 面向 LLM 的核心 API 文档
├── DATABASE.md                  # 数据库结构文档
├── PROTECT_SOURCE_GUIDE.md      # 源码保护方案指南
├── requirements.txt             # Python 依赖
└── README.md                    # 项目说明
```

---

## 📖 核心 API 文档

详细接口说明请参阅 [API_FOR_LLM.md](API_FOR_LLM.md)。

### 常用接口示例

```python
# 查询股票基本信息
from data_fetcher import query_stock_basic

# 查询A股上市公司
stocks = query_stock_basic(industry="银行")
print(stocks)

# 查询历史行情
from data_fetcher import query_daily_kline

# 获取某只股票的历史 K 线
klines = query_daily_kline(
    codes=["sz.000001"],
    start_date="2024-01-01",
    end_date="2024-12-31"
)
print(klines)
```

---

## 🛠️ 环境要求

| 依赖 | 版本要求 |
| :--- | :--- |
| Python | 3.6+ |
| OpenClaw | 或国内各种云端/本地 Claw 环境 |

### Python 依赖

```
requests
pandas
sqlalchemy
pycryptodome
```

---

## 🤝 贡献

欢迎提交 Pull Request 来改进这个项目！

期待各路英豪找出更多美妙的交易因子，走向财富自由之路 🚀

---

## 📜 许可证

Apache-2.0 License

Copyright © 2026 [BitSoulTech](https://www.aicodingyard.com)
