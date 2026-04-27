#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
导出排行榜前N个账户的MOE配置文件

用法: python export_top_configs.py --date 2026-03-20 --top 50 --output ./top_configs

参数:
    --date DATE     排行榜日期 (YYYY-MM-DD)
    --top NUM       导出前N个账户（默认50）
    --output DIR    输出文件夹路径（默认 ./export_top_configs）
    --ranking-dir DIR  排行榜目录（可选，默认自动查找最新目录）

说明:
    自动查找指定日期的排行榜CSV文件，提取前N个账户ID，
    然后将这些账户对应的moe_weights.json文件复制到输出目录。
"""

import os
import sys
import csv
import shutil
import argparse
from pathlib import Path

CLAW_POOL_DIR = r"d:\codebase\BitSoulStockSkill\claw_pool"

def find_ranking_dir(date: str = None) -> str:
    """查找排名目录"""
    if not os.path.exists(CLAW_POOL_DIR):
        print(f"错误: 目录不存在 {CLAW_POOL_DIR}")
        sys.exit(1)
    
    ranking_dirs = [d for d in os.listdir(CLAW_POOL_DIR) 
                    if d.startswith("ranking_") and os.path.isdir(os.path.join(CLAW_POOL_DIR, d))]
    
    if not ranking_dirs:
        print("错误: 未找到任何ranking目录")
        sys.exit(1)
    
    ranking_dirs.sort(key=lambda x: int(x.split("_")[1]) if "_" in x else 0, reverse=True)
    
    if date:
        for rd in ranking_dirs:
            ranking_file = os.path.join(CLAW_POOL_DIR, rd, f"ranking_{date}.csv")
            if os.path.exists(ranking_file):
                print(f"找到指定日期的排名目录: {rd}")
                return os.path.join(CLAW_POOL_DIR, rd)
        print(f"警告: 未找到 {date} 的排名文件，使用最新目录")
    
    print(f"使用最新排名目录: {ranking_dirs[0]}")
    return os.path.join(CLAW_POOL_DIR, ranking_dirs[0])

def export_top_configs(date: str, top_n: int, output_dir: str, ranking_dir: str = None):
    """导出前N个账户的MOE配置"""
    if ranking_dir is None:
        ranking_dir = find_ranking_dir(date)
    
    csv_file = os.path.join(ranking_dir, f"ranking_{date}.csv")
    if not os.path.exists(csv_file):
        print(f"错误: 排名文件不存在 {csv_file}")
        sys.exit(1)
    
    os.makedirs(output_dir, exist_ok=True)
    print(f"输出目录: {output_dir}")
    
    account_ids = []
    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= top_n:
                break
            account_ids.append(int(row['账户ID']))
    
    print(f"将导出前 {len(account_ids)} 个账户的MOE配置")
    
    copied = 0
    failed = []
    
    for acc_id in account_ids:
        src_weights = os.path.join(CLAW_POOL_DIR, "account", f"account_{acc_id:04d}", "moe_weights.json")
        
        if not os.path.exists(src_weights):
            src_weights = os.path.join(CLAW_POOL_DIR, f"account_{acc_id:04d}", "moe_weights.json")
        
        if not os.path.exists(src_weights):
            failed.append(acc_id)
            continue
        
        dst_dir = os.path.join(output_dir, f"account_{acc_id:04d}")
        os.makedirs(dst_dir, exist_ok=True)
        
        dst_weights = os.path.join(dst_dir, "moe_weights.json")
        shutil.copy2(src_weights, dst_weights)
        copied += 1
        
        print(f"  已导出: account_{acc_id:04d}")
    
    print(f"\n导出完成: {copied}/{len(account_ids)} 个账户")
    
    if failed:
        print(f"失败: {len(failed)} 个账户 - {failed[:10]}{'...' if len(failed) > 10 else ''}")
    
    manifest_file = os.path.join(output_dir, "manifest.csv")
    with open(manifest_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['account_id', 'total_return_pct', 'daily_return_pct', 'max_drawdown', 'sharpe_ratio'])
        
        with open(csv_file, 'r', encoding='utf-8-sig') as cf:
            reader = csv.DictReader(cf)
            for i, row in enumerate(reader):
                if i >= top_n:
                    break
                writer.writerow([
                    row['账户ID'],
                    row['总收益率(%)'],
                    row['当日收益率(%)'],
                    row['最大回撤(%)'],
                    row['夏普比率']
                ])
    
    print(f"清单文件: {manifest_file}")
    return output_dir

def main():
    parser = argparse.ArgumentParser(description='导出排行榜前N个账户的MOE配置文件')
    parser.add_argument('--date', required=True, help='排行榜日期 (YYYY-MM-DD)')
    parser.add_argument('--top', type=int, default=50, help='导出前N个账户（默认50）')
    parser.add_argument('--output', default='./export_top_configs', help='输出文件夹路径')
    parser.add_argument('--ranking-dir', help='排行榜目录（可选）')
    
    args = parser.parse_args()
    
    ranking_dir = args.ranking_dir if args.ranking_dir else None
    
    export_top_configs(args.date, args.top, args.output, ranking_dir)
    
    print(f"\n使用方法:")
    print(f"  1. 将输出目录中的配置复制到目标账户目录")
    print(f"  2. 或指定 --weights-dir 参数使用此目录运行模拟")

if __name__ == "__main__":
    main()