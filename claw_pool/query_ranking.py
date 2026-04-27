#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
查询claw_pool排名数据 - CSV中文版
用法: python query_ranking.py 2026-03-16 2026-03-20

默认查找最新的ranking目录
"""

import os
import sys
import csv
from datetime import datetime, timedelta

CLAW_POOL_DIR = r"d:\codebase\BitSoulStockSkill\claw_pool"

def find_latest_ranking_dir():
    """查找最新的排名目录"""
    dirs = [d for d in os.listdir(CLAW_POOL_DIR) if d.startswith("ranking_")]
    if not dirs:
        return None
    dirs.sort(key=lambda x: int(x.split("_")[1]) if "_" in x else 0, reverse=True)
    return os.path.join(CLAW_POOL_DIR, dirs[0])

def query_ranking(start_date: str, end_date: str):
    # 查找最新的ranking目录
    ranking_dir = find_latest_ranking_dir()
    
    if not ranking_dir or not os.path.exists(ranking_dir):
        print("错误: 未找到排名目录，请先运行模拟脚本")
        return
    
    print(f"使用排名目录: {ranking_dir}")
    print(f"查询日期范围: {start_date} ~ {end_date}")
    
    dates = []
    current = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    while current <= end:
        if current.weekday() < 5:
            dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    
    for date in dates:
        csv_file = os.path.join(ranking_dir, f"ranking_{date}.csv")
        
        if not os.path.exists(csv_file):
            print(f"\n[{date}] 无数据")
            continue
        
        print(f"\n{'='*100}")
        print(f"[{date}] 前10名排行（按当日收益率）")
        print(f"{'当日排名':<8}{'总排名':<8}{'账户ID':<8}{'总权益':<12}{'总收益%':<10}{'当日%':<10}{'回撤%':<8}{'夏普':<8}")
        print("-" * 90)
        
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
            for i, row in enumerate(rows[:10], 1):
                print(f"{row['当日排名']:<8}{row['总排名']:<8}{row['账户ID']:<8}{row['总权益']:<12}"
                      f"{row['总收益率(%)']:<10}{row['当日收益率(%)']:<10}{row['最大回撤(%)']:<8}{row['夏普比率']:<8}")
            
            print(f"\n  ... 共 {len(rows)} 个账户")
            print(f"  CSV文件: {csv_file}")

def main():
    if len(sys.argv) >= 3:
        query_ranking(sys.argv[1], sys.argv[2])
    else:
        print("用法: python query_ranking.py 2026-03-16 2026-03-20")

if __name__ == "__main__":
    main()