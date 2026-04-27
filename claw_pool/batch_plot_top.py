#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import csv
import argparse
from plot_lobster_curve import plot_lobster_returns

def plot_top_lobsters(csv_file: str, top_n: int = 5):
    if not os.path.exists(csv_file):
        print(f"错误: 找不到文件 {csv_file}")
        return

    ranking_dir = os.path.dirname(os.path.abspath(csv_file))
    profit_curves_dir = os.path.join(ranking_dir, "profit_curves")
    os.makedirs(profit_curves_dir, exist_ok=True)

    lobster_ids = []
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 检查是否存在“龙虾id”列
                if '龙虾id' in row:
                    lobster_ids.append(int(row['龙虾id']))
                elif 'account_id' in row:
                    lobster_ids.append(int(row['account_id']))
                else:
                    print("CSV 文件中没有找到 '龙虾id' 或 'account_id' 列。")
                    return
                
                if len(lobster_ids) >= top_n:
                    break
    except Exception as e:
        print(f"解析 CSV 文件失败: {e}")
        return

    if not lobster_ids:
        print("未在 CSV 中找到任何龙虾数据。")
        return

    print(f"==========================================")
    print(f"📊 将为排名前 {len(lobster_ids)} 的龙虾生成图表: {lobster_ids}")
    print(f"📂 图表将保存在: {profit_curves_dir}")
    print(f"==========================================\n")

    plot_lobster_returns(ranking_dir, lobster_ids, output_dir=profit_curves_dir)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='批量生成指定 CSV 文件中前 N 名龙虾的收益曲线')
    parser.add_argument('--file', required=True, help='CSV 排行榜文件路径，例如 d:\\...\\ranking_2026-04-09.csv')
    parser.add_argument('--top', type=int, default=5, help='生成前 N 名的图表，默认为 5')
    
    args = parser.parse_args()
    plot_top_lobsters(args.file, args.top)