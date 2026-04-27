#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import json
import csv
import time
import random
import signal
import argparse
from typing import List, Dict, Tuple

# 导入底层依赖
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from claw_pool_sim_runner import Account, generate_random_moe_weights, get_daily_stock_pool, load_daily_kline

# ============ 数据加载 ============
def load_real_data(trades_file: str, stats_file: str):
    real_trades = {}
    real_stats = {}
    
    with open(trades_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            date = row['date']
            if date not in real_trades:
                real_trades[date] = []
            real_trades[date].append(row)
            
    with open(stats_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            date = row['date']
            positions = {}
            if row['positions']:
                for item in row['positions'].split(';'):
                    if ':' in item:
                        code, shares = item.split(':')
                        positions[code] = int(shares)
            real_stats[date] = {
                'total_equity': float(row['total_equity']),
                'cash': float(row['cash']),
                'positions': positions
            }
            
    return real_trades, real_stats

# ============ GA账户类 ============
class GAAccount(Account):
    """
    修改后的Account，不写入文件系统，只在内存中模拟
    """
    def __init__(self, weights: dict, max_holdings: int, initial_cash: float = 1500000.0, target_codes: set = None):
        self.id = 0
        self.cash = initial_cash
        self.positions = {}
        self.history = []
        self.equity_curve = []
        self.target_codes = target_codes or set()
        
        # 不要调用父类的 init，避免写文件
        self.seed = weights.get('seed', random.randint(0, 2**32 - 1))
        self.max_holdings = weights.get('max_holdings', max_holdings)
        self.weights = weights

    def calculate_score(self, code: str, date: str, rng: random.Random) -> float:
        """
        重写打分函数：必须使用 MOE weights 计算得分，否则 GA 无法通过改变权重来优化结果！
        """
        klines = load_daily_kline(code, "2026-03-01", date)
        if not klines:
            return rng.random() * 0.5
            
        close = float(klines[-1]['close'])
        
        # 1. 技术面得分 (Technical)
        tech_score = 0.5
        if len(klines) >= 5:
            ma5 = sum(float(k['close']) for k in klines[-5:]) / 5
            # 如果股价站上MA5，技术面得分提升，受 ma5 权重影响
            tech_score += ((close - ma5) / ma5 * 10) * self.weights['technical'].get('ma5', 1.0)
            
        # 2. 动量得分 (Alpha)
        alpha_score = 0.5
        if len(klines) >= 2:
            prev_close = float(klines[-2]['close'])
            momentum = (close - prev_close) / prev_close * 10
            alpha_score += momentum * self.weights['alpha'].get('momentum', 1.0)
            
        # 3. 伪基本面和行为面 (由于缺乏数据库字段，使用代码哈希和权重产生确定性分化)
        # 将 code 的哈希值扩大，并且跟日期结合，让不同股票在不同维度的区分度拉满，给 GA 充足的抓手
        code_val = int(code.split('.')[0]) if '.' in code else sum(ord(c) for c in code)
        date_val = sum(ord(c) for c in date)
        
        # 让基本面和行为面具备极强的股票间区分度
        pseudo_fund = ((code_val * 13 + date_val) % 100) / 100.0
        fund_score = pseudo_fund * self.weights['fundamental'].get('pe', 1.0)
        
        pseudo_behav = ((code_val * 17 + date_val * 3) % 100) / 100.0
        behav_score = pseudo_behav * self.weights['behavior'].get('turnover', 1.0)
        
        # MOE 综合打分
        experts = self.weights.get('expert_weights', {})
        final_score = (
            tech_score * experts.get('technical', 0.25) +
            alpha_score * experts.get('alpha', 0.25) +
            fund_score * experts.get('fundamental', 0.25) +
            behav_score * experts.get('behavior', 0.25)
        )
        
        # 减少噪声的干扰，否则即使找到了正确权重，也会被随机噪声破坏排名
        noise = (rng.random() - 0.5) * 0.05
        return min(max(final_score + noise, 0.0), 1.0)

    # 减少选股池随机样本的干扰
    def select_stocks(self, date: str, pool_size: int = 15):
        """
        重写选股池：强制将用户的目标股票加入选股池，降低随机股票数量，减轻“买错导致满仓”的误伤。
        """
        all_stocks = get_daily_stock_pool(date)
        if not all_stocks:
            return []
            
        target_in_pool = sorted([c for c in self.target_codes if c in all_stocks])
        
        rng = random.Random(f"{self.seed}_{date}")
        rem_stocks = sorted(list(set(all_stocks) - set(target_in_pool)))
        
        sample_size = max(0, pool_size - len(target_in_pool))
        if len(rem_stocks) > sample_size:
            sampled = rng.sample(rem_stocks, sample_size)
        else:
            sampled = rem_stocks
            
        stock_pool = target_in_pool + sampled
        
        scores = []
        for code in stock_pool:
            score = self.calculate_score(code, date, rng)
            scores.append((code, score))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:self.max_holdings]

# ============ 适应度函数 ============
def evaluate_fitness(account: GAAccount, real_trades: dict, real_stats: dict, prioritize_equity: bool) -> float:
    score = 0.0
    total_days = len(real_stats)
    if total_days == 0:
        return 0.0

    # 每天进行比较
    for date, r_stat in real_stats.items():
        # 获取模拟数据
        sim_equity = account.cash
        sim_pos_value = 0
        sim_positions = {}
        
        # 需要找到这天的 equity 记录
        for e in account.equity_curve:
            if e['date'] == date:
                sim_equity = e['total_equity']
                break
                
        for code, pos in account.positions.items():
            sim_positions[code] = pos['shares']
            
        r_positions = r_stat['positions']
        r_equity = r_stat['total_equity']
        
        # 1. 持仓重合度 (Position Overlap)
        sim_codes = set(sim_positions.keys())
        r_codes = set(r_positions.keys())
        intersection = len(sim_codes.intersection(r_codes))
        union = len(sim_codes.union(r_codes))
        overlap_score = intersection / union if union > 0 else (1.0 if len(sim_codes) == 0 and len(r_codes) == 0 else 0.0)
        
        # 2. 交易动作重合度 (Trade Action Overlap)
        # 获取这天的交易
        sim_day_trades = [t for t in account.history if t['date'] == date]
        r_day_trades = real_trades.get(date, [])
        
        sim_actions = set(f"{t['action']}_{t['code']}" for t in sim_day_trades)
        r_actions = set(f"{t['action']}_{t['code']}" for t in r_day_trades)
        
        t_intersection = len(sim_actions.intersection(r_actions))
        t_union = len(sim_actions.union(r_actions))
        trade_score = t_intersection / t_union if t_union > 0 else (1.0 if len(sim_actions) == 0 and len(r_actions) == 0 else 0.0)
        
        # 3. 资金相似度 (Equity Similarity)
        # 差异比例
        equity_diff = abs(sim_equity - r_equity) / r_equity if r_equity > 0 else 1.0
        equity_score = max(0.0, 1.0 - equity_diff * 5) # 误差超过20%则得0分
        
        # 4. 风格/持仓数量相似度
        count_diff = abs(len(sim_codes) - len(r_codes))
        count_score = max(0.0, 1.0 - count_diff * 0.2) # 每差1个扣20%
        
        # 5. 精确打击奖励（对能够买中并且买对金额进行额外激励）
        exact_match_score = 0.0
        if intersection > 0:
            match_weights = 0
            for code in sim_codes.intersection(r_codes):
                sim_amt = sim_positions[code]
                r_amt = r_positions[code]
                # 计算两者的数量差异（资金匹配度）
                diff_ratio = abs(sim_amt - r_amt) / max(r_amt, 1)
                match_weights += max(0.0, 1.0 - diff_ratio)
            exact_match_score = match_weights / len(r_codes)
        
        if prioritize_equity:
            # 资金和风格为主
            day_score = equity_score * 40 + count_score * 20 + overlap_score * 20 + exact_match_score * 20
        else:
            # 动作和持仓为主
            day_score = overlap_score * 30 + exact_match_score * 30 + trade_score * 20 + equity_score * 20
            
        score += day_score
        
    return score / total_days

# ============ 遗传算法引擎 ============
def mutate_weights(weights: dict) -> dict:
    new_weights = json.loads(json.dumps(weights))
    
    # 20%概率变异随机种子
    if random.random() < 0.2:
        new_weights['seed'] = random.randint(0, 2**32 - 1)
        
    # 20%概率变异最大持仓数
    if random.random() < 0.2:
        new_weights['max_holdings'] = random.randint(4, 10)
        
    # 变异专家权重
    for k in new_weights['expert_weights']:
        if random.random() < 0.3:
            new_weights['expert_weights'][k] += random.uniform(-0.15, 0.15)
            new_weights['expert_weights'][k] = max(0.0, new_weights['expert_weights'][k])
            
    # 归一化专家权重
    total = sum(new_weights['expert_weights'].values())
    if total > 0:
        for k in new_weights['expert_weights']:
            new_weights['expert_weights'][k] /= total
            
    # 变异底层因子
    for cat in ['technical', 'alpha', 'fundamental', 'behavior']:
        for k in new_weights[cat]:
            if random.random() < 0.2:
                new_weights[cat][k] += random.uniform(-0.3, 0.3)
                new_weights[cat][k] = max(0.0, new_weights[cat][k])
                
    # 变异阈值
    if random.random() < 0.2:
        new_weights['signal_thresholds']['buy'] += random.uniform(-0.08, 0.08)
        new_weights['signal_thresholds']['buy'] = max(0.5, min(0.95, new_weights['signal_thresholds']['buy']))
    if random.random() < 0.2:
        new_weights['signal_thresholds']['sell'] += random.uniform(-0.08, 0.08)
        new_weights['signal_thresholds']['sell'] = max(0.05, min(0.5, new_weights['signal_thresholds']['sell']))
        
    return new_weights

def crossover(w1: dict, w2: dict) -> dict:
    new_weights = json.loads(json.dumps(w1))
    
    # 随机选择继承 w2 的模块
    if random.random() < 0.5:
        new_weights['expert_weights'] = json.loads(json.dumps(w2['expert_weights']))
    if random.random() < 0.5:
        new_weights['technical'] = json.loads(json.dumps(w2['technical']))
    if random.random() < 0.5:
        new_weights['alpha'] = json.loads(json.dumps(w2['alpha']))
    if random.random() < 0.5:
        new_weights['fundamental'] = json.loads(json.dumps(w2['fundamental']))
    if random.random() < 0.5:
        new_weights['behavior'] = json.loads(json.dumps(w2['behavior']))
    if random.random() < 0.5:
        new_weights['signal_thresholds'] = json.loads(json.dumps(w2['signal_thresholds']))
        
    return new_weights

# 优雅退出的全局标记
STOP_FLAG = False
def handle_sigint(sig, frame):
    global STOP_FLAG
    print("\n[!] 收到中断信号，准备保存进度并安全退出...")
    STOP_FLAG = True

def run_ga(real_trades_file, real_stats_file, max_time=3600, prioritize_equity=False, resume_file=None):
    signal.signal(signal.SIGINT, handle_sigint)
    
    real_trades, real_stats = load_real_data(real_trades_file, real_stats_file)
    dates = sorted(list(real_stats.keys()))
    if not dates:
        print("未找到有效数据！")
        return
        
    print(f"载入真实数据完成，时间跨度: {dates[0]} ~ {dates[-1]}")
    
    # 提取目标股票代码，用于强制加入选股池
    target_codes = set()
    for d, stat in real_stats.items():
        target_codes.update(stat['positions'].keys())
    for d, trades in real_trades.items():
        for t in trades:
            target_codes.add(t['code'])
    
    # 参数配置
    pop_size = 50
    generations = 100
    population = []
    
    # 初始化种群或加载断点
    start_gen = 0
    if resume_file and os.path.exists(resume_file):
        print(f"从 {resume_file} 恢复断点...")
        with open(resume_file, 'r', encoding='utf-8') as f:
            ckpt = json.load(f)
            population = ckpt['population']
            start_gen = ckpt['generation']
    else:
        print("初始化随机种群...")
        for _ in range(pop_size):
            population.append(generate_random_moe_weights())
            
    start_time = time.time()
    best_overall_score = -1
    best_overall_weights = None
    
    for gen in range(start_gen, generations):
        if STOP_FLAG or (time.time() - start_time) > max_time:
            print("\n达到时间上限或被中断，保存断点...")
            ckpt = {
                'generation': gen,
                'population': population,
                'best_score': best_overall_score,
                'best_weights': best_overall_weights
            }
            with open('checkpoint.json', 'w', encoding='utf-8') as f:
                json.dump(ckpt, f, ensure_ascii=False)
            print("进度已保存至 checkpoint.json")
            break
            
        print(f"\n--- 第 {gen+1} 代 ---")
        scores = []
        
        for idx, weights in enumerate(population):
            # 获取 initial_cash
            initial_cash = real_stats[dates[0]]['total_equity']
            acc = GAAccount(weights=weights, max_holdings=weights.get('max_holdings', 5), initial_cash=initial_cash, target_codes=target_codes)
            
            # 运行模拟
            for d in dates:
                acc.trade(d)
                acc.update_equity(d)
                
            score = evaluate_fitness(acc, real_trades, real_stats, prioritize_equity)
            scores.append((score, weights))
            
        # 排序
        scores.sort(key=lambda x: x[0], reverse=True)
        best_gen_score = scores[0][0]
        
        if best_gen_score > best_overall_score:
            best_overall_score = best_gen_score
            best_overall_weights = json.loads(json.dumps(scores[0][1]))
            # 自动保存当前最好的 weights
            with open('best_inferred_weights.json', 'w', encoding='utf-8') as f:
                json.dump(best_overall_weights, f, indent=2, ensure_ascii=False)
                
        print(f"本代最高分: {best_gen_score:.2f} / 历史最高分: {best_overall_score:.2f}")
        
        # 进化（选择、交叉、变异）
        new_population = []
        # 1. 精英保留 10%（保留历史最优）
        elite_count = int(pop_size * 0.1)
        for i in range(elite_count):
            new_population.append(json.loads(json.dumps(scores[i][1])))
            
        # 2. 引入 20% 全新随机个体（打破阶梯效应，强制保持基因多样性）
        random_count = int(pop_size * 0.2)
        for _ in range(random_count):
            new_population.append(generate_random_moe_weights())
            
        # 3. 剩下的 70% 通过交叉和变异产生
        while len(new_population) < pop_size:
            # 扩大父母选择范围到前 80%，防止近亲繁殖
            pool_size = int(pop_size * 0.8)
            p1 = random.choice(scores[:pool_size])[1]
            p2 = random.choice(scores[:pool_size])[1]
            
            child = crossover(p1, p2)
            # 提高变异概率，如果随机数满足条件则进行变异
            child = mutate_weights(child)
            new_population.append(child)
            
        population = new_population

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--trades', default='real_trades_template.csv')
    parser.add_argument('--stats', default='real_daily_stats_template.csv')
    parser.add_argument('--max-time', type=int, default=3600, help='最大运行时间(秒)')
    parser.add_argument('--prioritize-equity', action='store_true', help='开启此项则优先拟合资金曲线，不强求个股一致')
    parser.add_argument('--resume', type=str, default='', help='断点续训的文件路径')
    args = parser.parse_args()
    
    run_ga(args.trades, args.stats, args.max_time, args.prioritize_equity, args.resume)
