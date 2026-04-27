#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
随机搜索 MOE 权重和种子
用法: python random_search_runner.py --start 2026-03-16 --end 2026-03-20 --target-return 2.0 --target-count 100
"""

import os
import sys
import json
import random
import time
import argparse
from datetime import datetime, timedelta

# 导入 claw_pool_sim_runner 中的依赖
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from claw_pool_sim_runner import generate_random_moe_weights, Account, get_db_connection

CLAW_POOL_DIR = r"d:\codebase\BitSoulStockSkill\claw_pool"

class SearchAccount(Account):
    """
    重写 Account 类，避免在初始化时就往固定的 account 目录写入文件。
    将文件写入到传入的工作目录中。
    """
    def __init__(self, account_id: int, weights: dict, max_holdings: int, work_dir: str):
        self.id = account_id
        self.cash = 500000
        self.positions = {}
        self.history = []
        self.equity_curve = []
        
        self.dir = os.path.join(work_dir, f"temp_account_{account_id}")
        os.makedirs(self.dir, exist_ok=True)
        
        self.seed = weights.get('seed', random.randint(0, 2**32 - 1))
        self.max_holdings = weights.get('max_holdings', max_holdings)
        
        if 'seed' not in weights:
            weights['seed'] = self.seed
        if 'max_holdings' not in weights:
            weights['max_holdings'] = self.max_holdings
            
        self.weights = weights
        
        # 保存临时的权重文件
        weights_file = os.path.join(self.dir, "moe_weights.json")
        with open(weights_file, 'w', encoding='utf-8') as f:
            json.dump(weights, f, indent=2, ensure_ascii=False)

def get_trading_dates(start_date: str, end_date: str) -> list:
    """获取交易日列表（简单排除周末）"""
    dates = []
    current = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    while current <= end:
        if current.weekday() < 5:
            dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    return dates

def run_search(start_date: str, end_date: str, target_return: float, target_count: int):
    # 建立总文件夹
    timestamp = int(time.time())
    main_dir = os.path.join(CLAW_POOL_DIR, f"search_run_{timestamp}")
    os.makedirs(main_dir, exist_ok=True)
    
    print(f"开始随机搜索...")
    print(f"时间范围: {start_date} ~ {end_date}")
    print(f"目标收益率: > {target_return}%")
    print(f"目标寻找数量: {target_count}")
    print(f"总输出目录: {main_dir}\n")
    
    dates = get_trading_dates(start_date, end_date)
    if not dates:
        print("错误：没有找到有效的交易日")
        return

    success_count = 0
    attempts = 0
    
    while success_count < target_count:
        attempts += 1
        
        # 随机生成权重和参数
        weights = generate_random_moe_weights()
        seed = random.randint(0, 2**32 - 1)
        # 股票数量尽可能在4-7个间分布，不超过10个
        max_holdings = random.choice([4, 5, 6, 7, 8, 9, 10])
        # 增加4-7的权重，使其“尽可能在4-7个间分布”
        if random.random() < 0.7:
            max_holdings = random.randint(4, 7)
            
        weights['seed'] = seed
        weights['max_holdings'] = max_holdings
        
        # 创建搜索账户
        account = SearchAccount(account_id=attempts, weights=weights, max_holdings=max_holdings, work_dir=main_dir)
        
        # 运行模拟
        for date in dates:
            account.trade(date)
            account.update_equity(date)
            
        # 获取最终统计
        stats = account.get_stats(end_date)
        final_return = stats['total_return_pct']
        
        if final_return > target_return:
            success_count += 1
            # 满足条件，按计算结束的时间戳建一个文件夹
            success_timestamp = int(time.time())
            success_dir = os.path.join(main_dir, f"success_{success_timestamp}_{success_count}")
            os.makedirs(success_dir, exist_ok=True)
            
            # 保存权重和种子
            weights_file = os.path.join(success_dir, "moe_weights.json")
            with open(weights_file, 'w', encoding='utf-8') as f:
                json.dump(weights, f, indent=2, ensure_ascii=False)
                
            print(f"[{success_count}/{target_count}] 找到符合条件的配置! 尝试次数: {attempts}, 收益率: {final_return:.2f}%, 保存至: {os.path.basename(success_dir)}")
            
            # 清理临时账户文件夹
            try:
                import shutil
                shutil.rmtree(account.dir)
            except:
                pass
        else:
            # 不满足条件，清理临时文件夹，继续循环
            try:
                import shutil
                shutil.rmtree(account.dir)
            except:
                pass
                
        if attempts % 50 == 0:
            print(f"已尝试 {attempts} 次，当前成功找到 {success_count} 个配置...")

    print(f"\n搜索完成！共尝试 {attempts} 次，找到 {success_count} 个符合条件的配置。")
    print(f"所有结果保存在: {main_dir}")

def main():
    parser = argparse.ArgumentParser(description='随机搜索符合目标收益率的 MOE 权重和种子')
    parser.add_argument('--start', required=True, help='开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end', required=True, help='结束日期 (YYYY-MM-DD)')
    parser.add_argument('--target-return', type=float, default=2.0, help='目标总收益率阈值(%)，默认 2.0')
    parser.add_argument('--target-count', type=int, default=100, help='需要找到的成功配置数量，默认 100')
    
    args = parser.parse_args()
    
    run_search(args.start, args.end, args.target_return, args.target_count)

if __name__ == "__main__":
    main()
