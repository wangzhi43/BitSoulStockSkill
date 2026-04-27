#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
claw_pool 模拟运行脚本
用法: python claw_pool_sim_runner.py --start 2026-03-16 --end 2026-03-20 [--no-generate-weights]

参数:
    --start DATE         开始日期 (YYYY-MM-DD)
    --end DATE           结束日期 (YYYY-MM-DD)
    --no-generate-weights  禁用随机权重生成，使用已有权重文件夹
    --weights-dir DIR    指定权重文件夹路径（当 --no-generate-weights 时使用）
    --accounts NUM       账户数量（默认1000）
"""

import os
import sys
import json
import random
import sqlite3
import shutil
import csv
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import numpy as np

sys.path.insert(0, r"d:\codebase\BitSoulStockSkill\strategy-picker\scripts")

import data_fetcher
import config
import stock_api

# ============ 配置 ============
CLAW_POOL_DIR = r"d:\codebase\BitSoulStockSkill\claw_pool"
NUM_ACCOUNTS = 1000
INITIAL_CASH = 500000
MIN_CASH_RATIO = 0.1

RANKING_OUTPUT_DIR = None

# ============ 数据库连接 ============
DB_PATH = r"C:\Users\admin\AppData\Local\Temp\BitSoulStockSkill\data.db"

def get_db_connection():
    return sqlite3.connect(DB_PATH)

# ============ 缓存 ============
STOCK_NAME_CACHE = {}
STOCK_INFO_CACHE = {}
PREV_TRADING_DATE_CACHE = {}
ADJ_FACTOR_CACHE = {}
STOCK_LIMIT_CACHE = {}

def get_stock_name(code: str) -> str:
    """获取股票名称"""
    return get_stock_info(code)['name']

def get_stock_info(code: str) -> Dict[str, str]:
    """获取股票基础信息"""
    if code in STOCK_INFO_CACHE:
        return STOCK_INFO_CACHE[code]

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name, market, list_date FROM stock_basic WHERE ts_code = ? LIMIT 1",
        (code,),
    )
    row = cursor.fetchone()
    conn.close()

    info = {
        'name': row[0] if row and row[0] else code,
        'market': row[1] if row and row[1] else '',
        'list_date': row[2] if row and row[2] else '',
    }
    STOCK_INFO_CACHE[code] = info
    STOCK_NAME_CACHE[code] = info['name']
    return info

def get_prev_trading_date(date: str) -> Optional[str]:
    """获取给定日期之前的最近一个交易日"""
    if date in PREV_TRADING_DATE_CACHE:
        return PREV_TRADING_DATE_CACHE[date]

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT MAX(date) FROM daily_kline WHERE date < ?",
        (date,),
    )
    row = cursor.fetchone()
    conn.close()

    prev_date = row[0] if row and row[0] else None
    PREV_TRADING_DATE_CACHE[date] = prev_date
    return prev_date

def _compact_date(date: str) -> str:
    return date.replace("-", "")

def load_adj_factors(code: str, start_date: str, end_date: str) -> Dict[str, float]:
    """读取复权因子，用于规避分红送股导致的动量失真"""
    cache_key = (code, start_date, end_date)
    if cache_key in ADJ_FACTOR_CACHE:
        return ADJ_FACTOR_CACHE[cache_key]

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT trade_date, adj_factor
        FROM daily_basic
        WHERE ts_code = ? AND trade_date >= ? AND trade_date <= ?
        ORDER BY trade_date
        """,
        (code, _compact_date(start_date), _compact_date(end_date)),
    )
    result = {}
    for trade_date, adj_factor in cursor.fetchall():
        if trade_date:
            normalized = f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:8]}"
            result[normalized] = float(adj_factor) if adj_factor is not None else 1.0
    conn.close()

    ADJ_FACTOR_CACHE[cache_key] = result
    return result

def load_stock_limit_record(code: str, date: str) -> Optional[Dict[str, float]]:
    """优先读取正式涨跌停表，缺失时返回 None。"""
    cache_key = (code, date)
    if cache_key in STOCK_LIMIT_CACHE:
        return STOCK_LIMIT_CACHE[cache_key]

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT pre_close, up_limit, down_limit
        FROM stock_limit
        WHERE ts_code = ? AND REPLACE(trade_date, '-', '') = ?
        LIMIT 1
        """,
        (code, _compact_date(date)),
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        STOCK_LIMIT_CACHE[cache_key] = None
        return None

    record = {
        'pre_close': float(row[0] or 0),
        'up_limit': float(row[1] or 0),
        'down_limit': float(row[2] or 0),
    }
    STOCK_LIMIT_CACHE[cache_key] = record
    return record

def infer_limit_pct(code: str, date: str) -> Optional[float]:
    """推断涨跌停幅度；上市初期无涨跌幅限制时返回 None"""
    info = get_stock_info(code)
    name = (info.get('name') or '').upper()
    list_date = info.get('list_date') or ''

    if list_date:
        try:
            listed_days = (datetime.strptime(date, "%Y-%m-%d") - datetime.strptime(list_date, "%Y-%m-%d")).days
            if listed_days < 5:
                return None
        except ValueError:
            pass

    if code.endswith(".BJ"):
        return 0.30
    if code.startswith(("300", "301", "688", "689")):
        return 0.20
    if name.startswith("ST") or name.startswith("*ST"):
        return 0.05
    return 0.10

def _price_limit(code: str, date: str, pre_close: float, direction: str) -> Optional[float]:
    stock_limit = load_stock_limit_record(code, date)
    if stock_limit:
        limit_value = stock_limit['up_limit'] if direction == 'up' else stock_limit['down_limit']
        if limit_value > 0:
            return limit_value

    limit_pct = infer_limit_pct(code, date)
    if limit_pct is None or pre_close <= 0:
        return None

    factor = 1 + limit_pct if direction == 'up' else 1 - limit_pct
    return round(pre_close * factor, 2)

def _is_one_word_limit(code: str, row: Dict, direction: str) -> bool:
    """仅拦截日线可客观确认的一字板，避免在缺少盘口数据时过度假设。"""
    pre_close = float(row.get('pre_close') or 0)
    limit_price = _price_limit(code, row['date'], pre_close, direction)
    if limit_price is None:
        return False

    prices = [float(row.get(k) or 0) for k in ('open', 'high', 'low', 'close')]
    tolerance = max(0.01, abs(limit_price) * 0.001)
    return all(abs(price - limit_price) <= tolerance for price in prices)

def can_buy_on_row(code: str, row: Dict) -> bool:
    """当日开盘能否客观成交买入"""
    if float(row.get('open') or 0) <= 0 or float(row.get('volume') or 0) <= 0:
        return False
    return not _is_one_word_limit(code, row, 'up')

def can_sell_on_row(code: str, row: Dict) -> bool:
    """当日开盘能否客观成交卖出"""
    if float(row.get('open') or 0) <= 0 or float(row.get('volume') or 0) <= 0:
        return False
    return not _is_one_word_limit(code, row, 'down')

def normalize_buy_shares(shares: int) -> int:
    """A股买入最小交易单位为100股"""
    return max(0, (shares // 100) * 100)

def load_latest_kline(code: str, date: str) -> Optional[Dict]:
    """获取指定日期及之前最近一条日线，用于停牌估值"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT date, open, high, low, close, volume, pre_close, pctChg
        FROM daily_kline
        WHERE code = ? AND date <= ?
        ORDER BY date DESC
        LIMIT 1
        """,
        (code, date),
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return {
        'date': row[0],
        'open': row[1],
        'high': row[2],
        'low': row[3],
        'close': row[4],
        'volume': row[5],
        'pre_close': row[6],
        'pctChg': row[7],
    }

# ============ 数据加载 ============
DAILY_STOCK_POOL_CACHE = {}

def get_daily_stock_pool(date: str) -> List[str]:
    """获取当日可交易的股票池"""
    if date in DAILY_STOCK_POOL_CACHE:
        return DAILY_STOCK_POOL_CACHE[date]
        
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT DISTINCT code FROM daily_kline 
        WHERE date = '{date}' 
    """)
    stocks = [row[0] for row in cursor.fetchall()]
    stocks.sort()  # 排序以保证确定性
    conn.close()
    
    if not stocks:
        print(f"  警告: {date} 没有股票数据")
    
    DAILY_STOCK_POOL_CACHE[date] = stocks
    return stocks

def load_daily_kline(code: str, start_date: str, end_date: str) -> List[Dict]:
    """获取股票日线数据"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT date, open, high, low, close, volume, pre_close, pctChg
        FROM daily_kline
        WHERE code = ? AND date >= ? AND date <= ?
        ORDER BY date
        """,
        (code, start_date, end_date),
    )
    klines = [{
        'date': row[0],
        'open': row[1],
        'high': row[2],
        'low': row[3],
        'close': row[4],
        'volume': row[5],
        'pre_close': row[6],
        'pctChg': row[7],
    } for row in cursor.fetchall()]
    conn.close()
    return klines

# ============ MOE权重生成 ============
def generate_random_moe_weights() -> Dict:
    """生成随机MOE权重"""
    expert_weights = {
        'technical': random.uniform(0.0, 0.8),
        'alpha': random.uniform(0.0, 0.6),
        'fundamental': random.uniform(0.0, 0.4),
        'behavior': random.uniform(0.0, 0.4)
    }
    total = sum(expert_weights.values())
    if total > 0:
        for k in expert_weights:
            expert_weights[k] /= total
    else:
        expert_weights = {'technical': 0.4, 'alpha': 0.3, 'fundamental': 0.2, 'behavior': 0.1}
    
    technical = {
        'ma5': random.uniform(0.0, 2.0),
        'ma10': random.uniform(0.0, 2.0),
        'ma20': random.uniform(0.0, 2.0),
        'rsi': random.uniform(0.0, 2.0),
        'macd': random.uniform(0.0, 2.0),
        'kdj': random.uniform(0.0, 2.0),
        'boll': random.uniform(0.0, 2.0)
    }
    
    alpha = {
        'momentum': random.uniform(0.0, 2.0),
        'reversal': random.uniform(0.0, 2.0),
        'volume': random.uniform(0.0, 2.0)
    }
    
    fundamental = {
        'pe': random.uniform(0.0, 1.5),
        'pb': random.uniform(0.0, 1.5),
        'vol': random.uniform(0.0, 1.5)
    }
    
    behavior = {
        'turnover': random.uniform(0.0, 2.0),
        'block': random.uniform(0.0, 2.0)
    }
    
    return {
        "_version": 1,
        "expert_weights": expert_weights,
        "signal_thresholds": {
            "buy": random.uniform(0.5, 0.95),
            "sell": random.uniform(0.05, 0.5)
        },
        "technical": technical,
        "alpha": alpha,
        "fundamental": fundamental,
        "behavior": behavior
    }

# ============ 账户类 ============
class Account:
    """模拟账户"""
    def __init__(self, account_id: int, weights: Dict = None, max_holdings: int = None):
        self.id = account_id
        self.cash = INITIAL_CASH
        self.positions = {}
        self.history = []
        self.equity_curve = []
        
        self.dir = os.path.join(CLAW_POOL_DIR, "account", f"account_{account_id:04d}")
        os.makedirs(self.dir, exist_ok=True)
        
        if weights is None:
            weights = generate_random_moe_weights()
            self.seed = random.randint(0, 2**32 - 1)
            self.max_holdings = random.randint(4, 10)
            weights['seed'] = self.seed
            weights['max_holdings'] = self.max_holdings
        else:
            # 读取或补充种子与最大持仓数
            self.seed = weights.get('seed', random.randint(0, 2**32 - 1))
            self.max_holdings = weights.get('max_holdings', max_holdings if max_holdings else random.randint(4, 10))
            if 'seed' not in weights:
                weights['seed'] = self.seed
            if 'max_holdings' not in weights:
                weights['max_holdings'] = self.max_holdings
        
        weights_file = os.path.join(self.dir, "moe_weights.json")
        with open(weights_file, 'w', encoding='utf-8') as f:
            json.dump(weights, f, indent=2, ensure_ascii=False)
        
        self.weights = weights
    
    def calculate_score(self, code: str, date: str, rng: random.Random) -> float:
        """计算股票MOE评分"""
        score = rng.random() * 0.5 + 0.5
        
        klines = load_daily_kline(code, "2026-03-01", date)
        if len(klines) >= 5:
            recent = klines[-5:]
            adj_factors = load_adj_factors(code, recent[0]['date'], recent[-1]['date'])
            prices = [float(k['close']) * float(adj_factors.get(k['date'], 1.0) or 1.0) for k in recent]
            if prices[-1] > prices[0]:
                score += 0.1
        
        return min(score, 1.0)
    
    def select_stocks(self, date: str, pool_size: int = 50) -> List[Tuple[str, float]]:
        """选择股票池"""
        all_stocks = get_daily_stock_pool(date)
        
        if not all_stocks:
            return []
            
        # 根据账户seed和日期生成确定的随机数生成器
        rng = random.Random(f"{self.seed}_{date}")
        
        if len(all_stocks) > pool_size:
            stock_pool = rng.sample(all_stocks, pool_size)
        else:
            stock_pool = list(all_stocks)
        
        scores = []
        for code in stock_pool:
            score = self.calculate_score(code, date, rng)
            scores.append((code, score))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:self.max_holdings]
    
    def trade(self, date: str) -> List[Dict]:
        """每日交易"""
        trades = []
        signal_date = get_prev_trading_date(date)
        if not signal_date:
            return trades

        current_positions = list(self.positions.keys())
        selected = self.select_stocks(signal_date)
        top_codes = [s[0] for s in selected[:self.max_holdings]]
        
        for code in current_positions:
            if code not in top_codes:
                shares = self.positions[code]['shares']
                klines = load_daily_kline(code, date, date)
                if klines and can_sell_on_row(code, klines[0]):
                    price = float(klines[0]['open'])
                    self.cash += shares * price * 0.999
                    trades.append({
                        'date': date,
                        'signal_date': signal_date,
                        'code': code,
                        'name': get_stock_name(code),
                        'action': 'SELL',
                        'shares': shares,
                        'price': price,
                        'price_type': 'open',
                        'reason': 'score_down'
                    })
                    del self.positions[code]
        
        available_cash = self.cash * (1 - MIN_CASH_RATIO)
        for code, score in selected:
            if len(self.positions) >= self.max_holdings:
                break
            if code not in self.positions and available_cash > 10000:
                klines = load_daily_kline(code, date, date)
                if klines and can_buy_on_row(code, klines[0]):
                    price = float(klines[0]['open'])
                    slots_left = max(1, self.max_holdings - len(self.positions))
                    per_slot_budget = available_cash / slots_left
                    shares = normalize_buy_shares(int(per_slot_budget / price))
                    if shares >= 100:
                        cost = shares * price * 1.001
                        if cost <= self.cash:
                            self.cash -= cost
                            self.positions[code] = {'shares': shares, 'cost': price}
                            trades.append({
                                'date': date,
                                'signal_date': signal_date,
                                'code': code,
                                'name': get_stock_name(code),
                                'action': 'BUY',
                                'shares': shares,
                                'price': price,
                                'price_type': 'open',
                                'score': score
                            })
                            available_cash -= cost
        
        self.history.extend(trades)
        return trades
    
    def update_equity(self, date: str):
        """更新权益"""
        positions_value = 0
        for code, pos in self.positions.items():
            latest_kline = load_latest_kline(code, date)
            if latest_kline:
                price = float(latest_kline['close'])
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
            latest_kline = load_latest_kline(code, date)
            if latest_kline:
                price = float(latest_kline['close'])
                positions_value += pos['shares'] * price
        
        total_equity = self.cash + positions_value
        total_return = (total_equity - INITIAL_CASH) / INITIAL_CASH * 100
        
        daily_return = 0
        if len(self.equity_curve) > 1:
            prev_day = self.equity_curve[-2]['total_equity']
            if prev_day > 0:
                daily_return = (total_equity - prev_day) / prev_day * 100
        elif len(self.equity_curve) == 1:
            daily_return = (total_equity - INITIAL_CASH) / INITIAL_CASH * 100
        
        max_equity = INITIAL_CASH
        max_drawdown = 0
        for e in self.equity_curve:
            if e['total_equity'] > max_equity:
                max_equity = e['total_equity']
            dd = (max_equity - e['total_equity']) / max_equity * 100
            if dd > max_drawdown:
                max_drawdown = dd
        
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
        
        positions_with_name = [(get_stock_name(code), pos['shares']) for code, pos in self.positions.items()]
        
        return {
            'id': self.id,
            'date': date,
            'cash': round(self.cash, 2),
            'positions_value': round(positions_value, 2),
            'total_equity': round(total_equity, 2),
            'total_return_pct': round(total_return, 2),
            'daily_return_pct': round(daily_return, 2),
            'max_drawdown_pct': round(max_drawdown, 2),
            'sharpe_ratio': round(sharpe, 4),
            'positions_count': len(self.positions),
            'positions': positions_with_name
        }

# ============ 主函数 ============
def init_accounts(generate_weights: bool = True, weights_dir: str = None, 
                  num_accounts: int = 1000, keep_accounts: set = None) -> List[Account]:
    """初始化账户"""
    if keep_accounts is None:
        keep_accounts = set()
    
    os.makedirs(CLAW_POOL_DIR, exist_ok=True)
    
    print(f"初始化 {num_accounts} 个账户...")
    accounts = []
    
    for i in range(num_accounts):
        weights = None
        account_id = i + 1
        is_keep = account_id in keep_accounts
        
        if is_keep:
            weight_file = os.path.join(CLAW_POOL_DIR, "account", f"account_{account_id:04d}", "moe_weights.json")
            if os.path.exists(weight_file):
                with open(weight_file, 'r', encoding='utf-8') as f:
                    weights = json.load(f)
                print(f"  账户{account_id:04d}: 保留权重")
        elif not generate_weights and weights_dir:
            weight_file = os.path.join(weights_dir, f"account_{account_id:04d}", "moe_weights.json")
            if not os.path.exists(weight_file):
                weight_file = os.path.join(CLAW_POOL_DIR, "account", f"account_{account_id:04d}", "moe_weights.json")
            if os.path.exists(weight_file):
                with open(weight_file, 'r', encoding='utf-8') as f:
                    weights = json.load(f)
        
        account = Account(account_id, weights)
        accounts.append(account)
        
        if (i + 1) % 100 == 0:
            print(f"  已创建 {i+1}/{num_accounts}")
    
    print(f"账户初始化完成！")
    return accounts

def run_simulation(accounts: List[Account], start_date: str, end_date: str):
    """运行模拟"""
    dates = []
    current = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    while current <= end:
        if current.weekday() < 5:
            dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    
    print(f"\n运行模拟交易: {start_date} ~ {end_date}")
    print(f"交易日: {dates}")
    
    import time
    ranking_dir = os.path.join(CLAW_POOL_DIR, "ranking", f"ranking_{int(time.time())}")
    os.makedirs(ranking_dir, exist_ok=True)
    
    print(f"  排名目录: {ranking_dir}")
    
    global RANKING_OUTPUT_DIR
    RANKING_OUTPUT_DIR = ranking_dir
    
    for date in dates:
        print(f"\n处理日期: {date}")
        
        # 如果当天没有任何股票数据（如节假日、停牌或数据缺失），则跳过当天，不进行交易和市值计算
        # 否则会导致当天查不到收盘价，持仓市值被错误地算作0，从而引发巨大的虚假最大回撤
        if not get_daily_stock_pool(date):
            print(f"  跳过: {date} (无股票数据)")
            continue
            
        for account in accounts:
            trades = account.trade(date)
            account.update_equity(date)
        
        stats = [account.get_stats(date) for account in accounts]
        
        stats_with_total_rank = stats.copy()
        stats_with_total_rank.sort(key=lambda x: x['total_return_pct'], reverse=True)
        total_rank_map = {s['id']: i+1 for i, s in enumerate(stats_with_total_rank)}
        
        stats.sort(key=lambda x: x['total_return_pct'], reverse=True)
        
        for stat in stats:
            stat['total_rank'] = total_rank_map[stat['id']]
        
        os.makedirs(ranking_dir, exist_ok=True)
        
        ranking_file = os.path.join(ranking_dir, f"ranking_{date}.json")
        with open(ranking_file, 'w', encoding='utf-8') as f:
            json.dump(stats[:100], f, indent=2, ensure_ascii=False)
        
        csv_file = os.path.join(ranking_dir, f"ranking_{date}.csv")
        with open(csv_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                '总排名', '龙虾id', '持仓市值(万)', '账户总额(万)', 
                '总收益率(%)', '当日收益率(%)', '历史最大回撤(%)', '夏普比率', '持仓股票'
            ])
            for i, s in enumerate(stats[:100], 1):
                positions_str = '; '.join([f"{name}:{shares}股" for name, shares in s['positions']]) if s['positions'] else ''
                writer.writerow([
                    s['total_rank'], s['id'], round(s['positions_value'] / 10000, 1), 
                    round(s['total_equity'] / 10000, 1), s['total_return_pct'], s['daily_return_pct'],
                    s['max_drawdown_pct'], s['sharpe_ratio'], positions_str
                ])
        
        print(f"  已保存前100名账户数据")
        
        total_returns = [s['total_return_pct'] for s in stats]
        daily_returns = [s['daily_return_pct'] for s in stats]
        print(f"  当日最高: {max(daily_returns):.2f}%, 总收益最高: {max(total_returns):.2f}%")
        print(f"  收益最低: {min(total_returns):.2f}%")
    
    print(f"\n模拟完成！")
    print(f"结果保存在: {ranking_dir}")
    
    trades_dir = os.path.join(ranking_dir, "trades")
    os.makedirs(trades_dir, exist_ok=True)
    
    for s in stats[:100]:
        acc_id = s['id']
        acc = next((a for a in accounts if a.id == acc_id), None)
        if acc and acc.history:
            trade_file = os.path.join(trades_dir, f"account_{acc_id:04d}_trades.csv")
            with open(trade_file, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['日期', '信号日期', '动作', '股票代码', '股票名称', '数量', '价格', '成交价类型', '成交金额', '备注'])
                for t in acc.history:
                    amount = t['shares'] * t['price']
                    reason = t.get('reason', f"score: {t.get('score', 0):.4f}")
                    writer.writerow([
                        t['date'], t.get('signal_date', ''), t['action'], t['code'], t.get('name', ''),
                        t['shares'], f"{t['price']:.2f}", t.get('price_type', ''), f"{amount:.2f}", reason
                    ])
                    
    print(f"  已保存前100名账户的交易记录至 {trades_dir}")
    
    return ranking_dir

def main():
    parser = argparse.ArgumentParser(description='claw_pool 模拟运行脚本')
    parser.add_argument('--start', required=True, help='开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end', required=True, help='结束日期 (YYYY-MM-DD)')
    parser.add_argument('--no-generate-weights', action='store_true', 
                       help='禁用随机权重生成，使用已有权重文件夹')
    parser.add_argument('--weights-dir', help='指定权重文件夹路径')
    parser.add_argument('--accounts', type=int, default=1000, help='账户数量（默认1000）')
    parser.add_argument('--keep-accounts', help='保留权重的账户ID列表(JSON格式)')
    
    args = parser.parse_args()
    
    generate_weights = not args.no_generate_weights
    
    if not generate_weights and not args.weights_dir:
        print("错误: 使用 --no-generate-weights 时必须指定 --weights-dir")
        sys.exit(1)
    
    if args.weights_dir and not os.path.exists(args.weights_dir):
        print(f"错误: 权重目录不存在: {args.weights_dir}")
        sys.exit(1)
    
    print(f"配置:")
    print(f"  日期范围: {args.start} ~ {args.end}")
    print(f"  账户数量: {args.accounts}")
    print(f"  生成随机权重: {'否' if not generate_weights else '是'}")
    if args.weights_dir:
        print(f"  权重目录: {args.weights_dir}")
    
    keep_accounts = set()
    if args.keep_accounts:
        keep_accounts = set(json.loads(args.keep_accounts))
        print(f"  保留账户: {len(keep_accounts)}个")
    
    accounts = init_accounts(generate_weights, args.weights_dir, args.accounts, keep_accounts)
    ranking_dir = run_simulation(accounts, args.start, args.end)
    
    print(f"\n排名文件位置: {ranking_dir}")
    print(f"CSV文件: {os.path.join(ranking_dir, f'ranking_{args.end}.csv')}")

if __name__ == "__main__":
    main()
