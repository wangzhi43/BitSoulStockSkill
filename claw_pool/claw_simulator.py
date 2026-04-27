#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
claw_pool 模拟交易系统
1000个模拟账户，每个账户随机配置MOE权重，从2026-03-15开始模拟交易
"""

import os
import sys
import json
import random
import sqlite3
import shutil
import csv
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import pandas as pd
import numpy as np

sys.path.insert(0, r"d:\codebase\BitSoulStockSkill\strategy-picker\scripts")

import data_fetcher
import config
import define
import stock_api
from track_logger import TrackLogger
from logger import log

# ============ 配置 ============
CLAW_POOL_DIR = r"d:\codebase\BitSoulStockSkill\claw_pool"
NUM_ACCOUNTS = 1000
INITIAL_CASH = 500000  # 50万
START_DATE = "2026-03-15"
END_DATE = "2026-03-20"
MAX_HOLDINGS = 10  # 最多持仓10只
MIN_CASH_RATIO = 0.1  # 保留10%现金

RANKING_OUTPUT_DIR = None  # 排名输出目录

# ============ 数据库连接 ============
DB_PATH = r"C:\Users\admin\AppData\Local\Temp\BitSoulStockSkill\data.db"

def get_db_connection():
    return sqlite3.connect(DB_PATH)

# ============ 股票代码转名称 ============
STOCK_NAME_CACHE = {}

def get_stock_name(code: str) -> str:
    """获取股票名称"""
    if code in STOCK_NAME_CACHE:
        return STOCK_NAME_CACHE[code]
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT name FROM stock_basic WHERE ts_code = '{code}' LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    
    name = row[0] if row else code
    STOCK_NAME_CACHE[code] = name
    return name

# ============ 加载基础数据 ============
def load_stock_pool(date: str, limit: int = 100) -> List[str]:
    """获取当日可交易的股票池（随机抽取部分作为选股池）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT DISTINCT code FROM daily_kline 
        WHERE date = '{date}' 
        ORDER BY RANDOM() 
        LIMIT {limit}
    """)
    stocks = [row[0] for row in cursor.fetchall()]
    conn.close()
    return stocks

def load_daily_kline(code: str, start_date: str, end_date: str) -> List[Dict]:
    """获取股票日线数据"""
    conn = get_db_connection()
    df = pd.read_sql(f"""
        SELECT * FROM daily_kline 
        WHERE code = '{code}' AND date >= '{start_date}' AND date <= '{end_date}'
        ORDER BY date
    """, conn)
    conn.close()
    return df.to_dict('records') if not df.empty else []

def load_daily_basic(code: str, date: str) -> Optional[Dict]:
    """获取股票基本面数据"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT * FROM daily_basic 
        WHERE ts_code = '{code}' AND trade_date = '{date}'
    """)
    row = cursor.fetchone()
    conn.close()
    if row:
        cols = [desc[0] for desc in cursor.description]
        return dict(zip(cols, row))
    return None

# ============ MOE权重生成 ============
def generate_random_moe_weights() -> Dict:
    """随机生成MOE权重配置"""
    # 基础权重文件
    base_weights_path = r"d:\codebase\BitSoulStockSkill\strategy-picker\scripts\moe_weights.json"
    with open(base_weights_path, 'r', encoding='utf-8') as f:
        base = json.load(f)
    
    # 随机扰动专家权重
    expert_weights = base.get('expert_weights', {})
    total = sum(expert_weights.values())
    new_expert = {}
    for k, v in expert_weights.items():
        # -30% ~ +30% 随机扰动
        factor = 1 + random.uniform(-0.3, 0.3)
        new_expert[k] = v * factor
    # 归一化
    new_total = sum(new_expert.values())
    new_expert = {k: v/new_total for k, v in new_expert.items()}
    
    # 技术因子随机权重
    technical = base.get('technical', {})
    new_technical = {}
    for k, v in technical.items():
        factor = 1 + random.uniform(-0.5, 0.5)
        new_technical[k] = v * factor
    
    # Alpha因子随机权重
    alpha = base.get('alpha', {})
    new_alpha = {}
    for k, v in alpha.items():
        factor = 1 + random.uniform(-0.4, 0.4)
        new_alpha[k] = v * factor
    
    # 基本面因子
    fundamental = base.get('fundamental', {})
    new_fundamental = {}
    for k, v in fundamental.items():
        factor = 1 + random.uniform(-0.3, 0.3)
        new_fundamental[k] = v * factor
    
    # 行为因子
    behavior = base.get('behavior', {})
    new_behavior = {}
    for k, v in behavior.items():
        factor = 1 + random.uniform(-0.3, 0.3)
        new_behavior[k] = v * factor
    
    # 买卖阈值随机
    signal_thresholds = base.get('signal_thresholds', {})
    buy_thresh = signal_thresholds.get('buy', 0.7) * random.uniform(0.8, 1.2)
    sell_thresh = signal_thresholds.get('sell', 0.35) * random.uniform(0.8, 1.2)
    
    result = {
        "_comment": f"Account weights - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "_version": 1,
        "expert_weights": new_expert,
        "signal_thresholds": {
            "buy": min(buy_thresh, 0.95),
            "sell": max(sell_thresh, 0.1)
        },
        "technical": new_technical,
        "alpha": new_alpha,
        "fundamental": new_fundamental,
        "behavior": new_behavior
    }
    
    return result

# ============ 账户管理 ============
class Account:
    """模拟账户"""
    def __init__(self, account_id: int):
        self.id = account_id
        self.cash = INITIAL_CASH
        self.positions = {}  # {code: {'shares': int, 'cost': float}}
        self.history = []  # 交易历史
        self.equity_curve = []  # 权益曲线
        
        # 创建账户目录
        self.dir = os.path.join(CLAW_POOL_DIR, f"account_{account_id:04d}")
        os.makedirs(self.dir, exist_ok=True)
        
        # 保存随机权重
        weights = generate_random_moe_weights()
        weights_file = os.path.join(self.dir, "moe_weights.json")
        with open(weights_file, 'w', encoding='utf-8') as f:
            json.dump(weights, f, indent=2, ensure_ascii=False)
        
        self.weights = weights
    
    def calculate_score(self, code: str, date: str) -> float:
        """计算股票MOE评分（简化版）"""
        # 模拟评分：基于随机因子+技术指标
        score = random.random() * 0.5 + 0.5  # 0.5~1.0
        
        # 简单技术因子
        klines = load_daily_kline(code, "2026-03-01", date)
        if len(klines) >= 5:
            # 简单动量因子
            recent = klines[-5:]
            prices = [float(k['close']) for k in recent]
            if prices[-1] > prices[0]:
                score += 0.1
        
        return min(score, 1.0)
    
    def select_stocks(self, date: str, pool_size: int = 50) -> List[Tuple[str, float]]:
        """选择股票池"""
        stock_pool = load_stock_pool(date, pool_size)
        scores = []
        for code in stock_pool:
            score = self.calculate_score(code, date)
            scores.append((code, score))
        
        # 按评分排序
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:MAX_HOLDINGS]
    
    def trade(self, date: str) -> List[Dict]:
        """每日交易"""
        trades = []
        
        # 获取当前持仓
        current_positions = list(self.positions.keys())
        
        # 选股
        selected = self.select_stocks(date)
        
        # 卖出信号（简化：持有超过5天且评分下降）
        for code in current_positions:
            if code not in [s[0] for s in selected[:5]]:
                # 卖出
                shares = self.positions[code]['shares']
                klines = load_daily_kline(code, date, date)
                if klines:
                    price = float(klines[0]['close'])
                    self.cash += shares * price * 0.999  # 扣手续费
                    trades.append({
                        'date': date,
                        'code': code,
                        'action': 'SELL',
                        'shares': shares,
                        'price': price,
                        'reason': 'score_down'
                    })
                    del self.positions[code]
        
        # 买入信号
        available_cash = self.cash * (1 - MIN_CASH_RATIO)
        for code, score in selected:
            if len(self.positions) >= MAX_HOLDINGS:
                break
            if code not in self.positions and available_cash > 10000:
                klines = load_daily_kline(code, date, date)
                if klines:
                    price = float(klines[0]['close'])
                    shares = int(available_cash / price / MAX_HOLDINGS)
                    if shares > 0:
                        cost = shares * price * 1.001  # 含手续费
                        if cost <= self.cash:
                            self.cash -= cost
                            self.positions[code] = {'shares': shares, 'cost': price}
                            trades.append({
                                'date': date,
                                'code': code,
                                'action': 'BUY',
                                'shares': shares,
                                'price': price,
                                'score': score
                            })
                            available_cash -= cost
        
        return trades
    
    def update_equity(self, date: str):
        """更新权益"""
        positions_value = 0
        for code, pos in self.positions.items():
            klines = load_daily_kline(code, date, date)
            if klines:
                price = float(klines[0]['close'])
                positions_value += pos['shares'] * price
        
        total_equity = self.cash + positions_value
        self.equity_curve.append({
            'date': date,
            'cash': self.cash,
            'positions_value': positions_value,
            'total_equity': total_equity
        })
    
    def get_stats(self, date: str) -> Dict:
        """获取账户统计"""
        positions_value = 0
        for code, pos in self.positions.items():
            klines = load_daily_kline(code, date, date)
            if klines:
                price = float(klines[0]['close'])
                positions_value += pos['shares'] * price
        
        total_equity = self.cash + positions_value
        
        # 总收益率（从开始到现在）
        total_return = (total_equity - INITIAL_CASH) / INITIAL_CASH * 100
        
        # 每日收益率：从权益曲线中获取前一天的权益计算
        daily_return = 0
        if len(self.equity_curve) > 1:
            prev_day = self.equity_curve[-2]['total_equity']
            if prev_day > 0:
                daily_return = (total_equity - prev_day) / prev_day * 100
        elif len(self.equity_curve) == 1:
            prev_day = self.equity_curve[-1]['total_equity']
            if prev_day > 0:
                daily_return = (total_equity - prev_day) / prev_day * 100
        
        # 计算累计最大回撤
        max_equity = INITIAL_CASH
        max_drawdown = 0
        for e in self.equity_curve:
            if e['total_equity'] > max_equity:
                max_equity = e['total_equity']
            dd = (max_equity - e['total_equity']) / max_equity * 100
            if dd > max_drawdown:
                max_drawdown = dd
        
        # 计算累计夏普比率（从第一天开始）
        if len(self.equity_curve) > 1:
            returns = []
            for i in range(1, len(self.equity_curve)):
                prev_equity = self.equity_curve[i-1]['total_equity']
                if prev_equity > 0:
                    r = (self.equity_curve[i]['total_equity'] - prev_equity) / prev_equity
                    returns.append(r)
            if returns and np.std(returns) > 0:
                sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252)
            else:
                sharpe = 0
        else:
            sharpe = 0
        
        # 持仓股票转名称
        positions_with_name = [(get_stock_name(code), pos['shares']) for code, pos in self.positions.items()]
        
        return {
            'id': self.id,
            'date': date,
            'cash': round(self.cash, 2),
            'positions_value': round(positions_value, 2),
            'total_equity': round(total_equity, 2),
            'total_return_pct': round(total_return, 2),      # 总收益率
            'daily_return_pct': round(daily_return, 2),      # 每日收益率
            'max_drawdown_pct': round(max_drawdown, 2),      # 累计最大回撤
            'sharpe_ratio': round(sharpe, 4),                # 累计夏普比率
            'positions_count': len(self.positions),
            'positions': positions_with_name
        }

# ============ 主程序 ============
def init_accounts():
    """初始化所有账户"""
    os.makedirs(CLAW_POOL_DIR, exist_ok=True)
    
    print(f"初始化 {NUM_ACCOUNTS} 个账户...")
    accounts = []
    
    for i in range(NUM_ACCOUNTS):
        account = Account(i + 1)
        accounts.append(account)
        if (i + 1) % 100 == 0:
            print(f"  已创建 {i+1}/{NUM_ACCOUNTS}")
    
    print(f"账户初始化完成！")
    return accounts

def run_simulation(accounts: List[Account], start_date: str, end_date: str):
    """运行模拟"""
    # 生成交易日列表
    dates = []
    current = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    while current <= end:
        if current.weekday() < 5:  # 工作日
            dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    
    print(f"\n运行模拟交易: {start_date} ~ {end_date}")
    print(f"交易日: {dates}")
    
    # 清理旧的排名文件
    old_ranking_dir = os.path.join(CLAW_POOL_DIR, "ranking")
    backup_dir = os.path.join(CLAW_POOL_DIR, "ranking_old")
    if os.path.exists(old_ranking_dir):
        import shutil
        if os.path.exists(backup_dir):
            try:
                shutil.rmtree(backup_dir)
            except:
                pass
        try:
            os.rename(old_ranking_dir, backup_dir)
        except Exception as e:
            print(f"  警告: 备份旧文件失败: {e}")
    
    # 使用新目录
    import time
    ranking_dir = os.path.join(CLAW_POOL_DIR, f"ranking_{int(time.time())}")
    os.makedirs(ranking_dir, exist_ok=True)
    
    print(f"  排名目录: {ranking_dir}")
    
    # 导出ranking_dir供外部使用
    global RANKING_OUTPUT_DIR
    RANKING_OUTPUT_DIR = ranking_dir
    
    for date in dates:
        print(f"\n处理日期: {date}")
        for account in accounts:
            # 交易
            trades = account.trade(date)
            # 更新权益
            account.update_equity(date)
        
        # 每日统计
        stats = [account.get_stats(date) for account in accounts]
        
        # 计算总排名（按总收益率）
        stats_with_total_rank = stats.copy()
        stats_with_total_rank.sort(key=lambda x: x['total_return_pct'], reverse=True)
        total_rank_map = {s['id']: i+1 for i, s in enumerate(stats_with_total_rank)}
        
        # 按总收益率排序（而不是当日收益率）
        stats.sort(key=lambda x: x['total_return_pct'], reverse=True)
        
        # 保存排名
        os.makedirs(ranking_dir, exist_ok=True)
        
        # 保存JSON
        ranking_file = os.path.join(ranking_dir, f"ranking_{date}.json")
        with open(ranking_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        
        # 保存CSV（中文表头）
        csv_file = os.path.join(ranking_dir, f"ranking_{date}.csv")
        with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                '当日排名', '总排名', '账户ID', '现金余额', '持仓市值', '总权益', 
                '总收益率(%)', '当日收益率(%)', '最大回撤(%)', '夏普比率', '持仓数量', '持仓股票'
            ])
            for i, stat in enumerate(stats, 1):
                positions_str = '; '.join([f"{name}:{shares}股" for name, shares in stat['positions']])
                writer.writerow([
                    i, total_rank_map[stat['id']], stat['id'], round(stat['cash'], 2), round(stat['positions_value'], 2),
                    round(stat['total_equity'], 2), round(stat['total_return_pct'], 2), round(stat['daily_return_pct'], 2),
                    round(stat['max_drawdown_pct'], 2), round(stat['sharpe_ratio'], 4),
                    stat['positions_count'], positions_str
                ])
        
        print(f"  当日最高: {stats[0]['daily_return_pct']:.2f}%, 总收益最高: {stats_with_total_rank[0]['total_return_pct']:.2f}%")
        print(f"  收益最低: {stats[-1]['total_return_pct']:.2f}%")

def main():
    # 初始化账户
    accounts = init_accounts()
    
    # 运行模拟
    run_simulation(accounts, START_DATE, END_DATE)
    
    print("\n模拟完成！")
    print(f"结果保存在: {CLAW_POOL_DIR}")

if __name__ == "__main__":
    main()