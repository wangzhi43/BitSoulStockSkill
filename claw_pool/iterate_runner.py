#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
迭代优化脚本 - 寻找高收益账户配置
重复运行模拟，保留收益率超过10%的账户配置，重置未达标的配置

用法: python claw_pool\iterate_runner.py
"""

import os
import sys
import json
import subprocess
import csv
import argparse
from datetime import datetime

CLAW_POOL_DIR = r"d:\codebase\BitSoulStockSkill\claw_pool"
START_DATE = "2026-03-16"
TARGET_DATE = "2026-03-20"
END_DATE = "2026-03-20"
TOP_N = 20
MAX_ITERATIONS = 10

def get_account_dir(account_id: int) -> str:
    return os.path.join(CLAW_POOL_DIR, "account", f"account_{account_id:04d}")

def get_weights_file(account_id: int) -> str:
    return os.path.join(get_account_dir(account_id), "moe_weights.json")

def get_ranking_file(ranking_dir: str, date: str) -> str:
    return os.path.join(ranking_dir, f"ranking_{date}.csv")

def find_latest_ranking_dir() -> str:
    ranking_base = os.path.join(CLAW_POOL_DIR, "ranking")
    if not os.path.exists(ranking_base):
        return None
    
    dirs = [d for d in os.listdir(ranking_base) if d.startswith("ranking_")]
    if not dirs:
        return None
    
    dirs.sort(key=lambda x: os.path.getmtime(os.path.join(ranking_base, x)), reverse=True)
    return os.path.join(ranking_base, dirs[0])

def read_top_accounts(ranking_dir: str, date: str) -> list:
    csv_file = get_ranking_file(ranking_dir, date)
    if not os.path.exists(csv_file):
        return []
    
    top_accounts = []
    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            account_id = int(row['账户ID'])
            total_return = float(row['总收益率(%)'])
            top_accounts.append({'id': account_id, 'return': total_return})
    
    return top_accounts[:TOP_N]

def read_all_accounts(ranking_dir: str, date: str) -> list:
    csv_file = get_ranking_file(ranking_dir, date)
    if not os.path.exists(csv_file):
        return []
    
    all_accounts = []
    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            account_id = int(row['账户ID'])
            total_return = float(row['总收益率(%)'])
            all_accounts.append({'id': account_id, 'return': total_return})
    
    all_accounts.sort(key=lambda x: x['return'], reverse=True)
    return all_accounts

def get_keep_and_regen_accounts(ranking_dir: str) -> tuple:
    all_accounts = read_all_accounts(ranking_dir, TARGET_DATE)
    
    keep_accounts = set()
    regen_count = 0
    
    print(f"\n{TARGET_DATE} 所有账户收益（按收益率降序）:")
    for i, acc in enumerate(all_accounts, 1):
        if acc['return'] > 0:
            keep_accounts.add(acc['id'])
            print(f"  {i:3d}. 账户{acc['id']:04d}: {acc['return']:+.2f}% ✓ 保留")
        else:
            if i <= 20:
                print(f"  {i:3d}. 账户{acc['id']:04d}: {acc['return']:+.2f}% ✗ 待重置")
            regen_count += 1
    
    print(f"\n保留账户: {len(keep_accounts)}个, 待重置: {regen_count}个")
    return keep_accounts, regen_count

def check_convergence(ranking_dir: str) -> bool:
    all_accounts = read_all_accounts(ranking_dir, TARGET_DATE)
    
    print(f"\n{TARGET_DATE} 前{TOP_N}名账户收益:")
    for i, acc in enumerate(all_accounts[:TOP_N], 1):
        status = "✓" if acc['return'] > 0 else "✗"
        print(f"  {i}. 账户{acc['id']:04d}: {acc['return']:+.2f}% {status}")
    
    positive_count = sum(1 for acc in all_accounts[:TOP_N] if acc['return'] > 0)
    return positive_count >= TOP_N

def get_accounts_above_threshold(ranking_dir: str) -> set:
    return get_keep_and_regen_accounts(ranking_dir)[0]

def merge_and_save_rankings(ranking_dir: str, kept_accounts_data: dict, date: str) -> set:
    csv_file = get_ranking_file(ranking_dir, date)
    if not os.path.exists(csv_file):
        return set(kept_accounts_data.keys())
    
    new_accounts_data = []
    fieldnames = []
    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            new_accounts_data.append(row)
            
    merged_data = {}
    
    for acc_id, row in kept_accounts_data.items():
        merged_data[acc_id] = row
        
    for row in new_accounts_data:
        acc_id = int(row['账户ID'])
        if acc_id not in merged_data:
            merged_data[acc_id] = row
            ret = float(row['总收益率(%)'])
            if ret > 0:
                kept_accounts_data[acc_id] = row
                
    sorted_rows = sorted(merged_data.values(), key=lambda x: float(x['总收益率(%)']), reverse=True)
    
    for i, row in enumerate(sorted_rows, 1):
        row['当日排名'] = i
        row['总排名'] = i
        
    with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sorted_rows[:100])
        
    return set(kept_accounts_data.keys())

def get_positive_accounts_from_csv(csv_path: str) -> dict:
    if not os.path.exists(csv_path):
        print(f"警告: CSV文件不存在 - {csv_path}")
        return {}
    
    keep = {}
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            if '账户ID' not in reader.fieldnames or '总收益率(%)' not in reader.fieldnames:
                print("警告: CSV文件缺少'账户ID'或'总收益率(%)'字段")
                return {}
            
            for row in reader:
                try:
                    acc_id = int(row['账户ID'])
                    ret = float(row['总收益率(%)'])
                    if ret > 0:
                        keep[acc_id] = row
                except ValueError:
                    pass
        return keep
    except Exception as e:
        print(f"警告: 读取CSV文件失败 - {str(e)}")
        return {}

def run_simulation(keep_accounts: set):
    print(f"\n{'='*50}")
    print(f"运行模拟，保留账户: {len(keep_accounts)}个")
    for acc_id in sorted(keep_accounts):
        print(f"  - 账户{acc_id:04d}")
    
    cmd = [
        sys.executable,
        os.path.join(CLAW_POOL_DIR, "claw_pool_sim_runner.py"),
        "--start", START_DATE,
        "--end", END_DATE,
        "--keep-accounts", json.dumps(list(keep_accounts))
    ]
    
    print(f"命令: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"模拟运行失败: {result.stderr}")
        return None
    
    print(result.stdout)
    
    return find_latest_ranking_dir()

def main():
    parser = argparse.ArgumentParser(description='迭代优化脚本 - 寻找高收益账户配置')
    parser.add_argument('--csv-file', help='指定包含保护账户的CSV文件路径')
    args = parser.parse_args()
    
    print(f"迭代优化脚本")
    print(f"{'='*50}")
    print(f"目标日期: {TARGET_DATE}")
    print(f"目标: 前{TOP_N}账户总收益率 > 0%")
    print(f"最大迭代: {MAX_ITERATIONS}次")
    print(f"日期范围: {START_DATE} ~ {END_DATE}")
    
    iteration = 0
    kept_accounts_data = {}
    
    if args.csv_file:
        print(f"\n正在从CSV文件加载初始保护账户: {args.csv_file}")
        kept_accounts_data = get_positive_accounts_from_csv(args.csv_file)
        print(f"成功加载 {len(kept_accounts_data)} 个收益率大于0的账户")
        
    best_ranking_dir = None
    
    while iteration < MAX_ITERATIONS:
        iteration += 1
        print(f"\n{'#'*50}")
        print(f"第 {iteration}/{MAX_ITERATIONS} 次迭代")
        
        keep_accounts = set(kept_accounts_data.keys())
        ranking_dir = run_simulation(keep_accounts)
        
        if ranking_dir is None:
            print("模拟失败，停止迭代")
            break
        
        # 合并历史正收益数据到新结果中
        merge_and_save_rankings(ranking_dir, kept_accounts_data, TARGET_DATE)
        
        best_ranking_dir = ranking_dir
        
        if check_convergence(ranking_dir):
            print(f"\n🎉 收敛成功！前{TOP_N}账户全部为正收益")
            break
        
        # get_keep_and_regen_accounts 会打印当前排名状态，但不影响 kept_accounts_data
        _, regen_count = get_keep_and_regen_accounts(ranking_dir)
        
        if iteration >= MAX_ITERATIONS:
            print(f"\n达到最大迭代次数 {MAX_ITERATIONS}，停止")
    
    print(f"\n{'='*50}")
    print(f"迭代完成")
    if best_ranking_dir:
        print(f"最终排名目录: {best_ranking_dir}")
        check_convergence(best_ranking_dir)

if __name__ == "__main__":
    main()