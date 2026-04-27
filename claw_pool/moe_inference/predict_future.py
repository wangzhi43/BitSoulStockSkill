#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import json
import csv
import argparse

# 导入底层依赖
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from claw_pool_sim_runner import Account, get_db_connection

def get_future_dates(start_date: str, days: int) -> list:
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT DISTINCT date FROM daily_kline WHERE date > ? ORDER BY date LIMIT ?", (start_date, days))
    dates = [row[0] for row in c.fetchall()]
    conn.close()
    return dates

def get_last_price(code: str, date: str) -> float:
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT close FROM daily_kline WHERE code = ? AND date <= ? ORDER BY date DESC LIMIT 1", (code, date))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0.0

def run_prediction(weights_file: str, stats_file: str, predict_days: int):
    if not os.path.exists(weights_file):
        print(f"[错误] 找不到权重文件 {weights_file}，请先运行 ga_runner.py 进行拟合。")
        return

    with open(weights_file, 'r', encoding='utf-8') as f:
        weights = json.load(f)

    # 读取最后一日的状态
    last_date = None
    last_cash = 0.0
    last_positions = {}
    
    if not os.path.exists(stats_file):
        print(f"[错误] 找不到历史数据文件 {stats_file}。")
        return
        
    with open(stats_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            last_date = row['date']
            last_cash = float(row['cash'])
            pos_str = row['positions']
            if pos_str:
                for item in pos_str.split(';'):
                    if ':' in item:
                        code, shares = item.split(':')
                        last_positions[code] = int(shares)

    if not last_date:
        print("[错误] 未能从统计文件中读取到历史状态。")
        return

    print(f"========== 状态初始化 ==========")
    print(f"基于 {last_date} 的真实状态开始预测...")
    print(f"可用资金: {last_cash:.2f}")
    print(f"当前持仓: {last_positions}")

    # 获取未来N个交易日
    future_dates = get_future_dates(last_date, predict_days)
    if not future_dates:
        print("[错误] 数据库中没有找到后续的交易日数据。")
        return
        
    print(f"预测日期范围: {future_dates[0]} 至 {future_dates[-1]} ({len(future_dates)}天)\n")

    # 初始化账户
    account = Account(account_id=9999, weights=weights, max_holdings=weights.get('max_holdings', 5))
    account.cash = last_cash
    
    # 填充历史持仓和成本
    for code, shares in last_positions.items():
        cost = get_last_price(code, last_date)
        account.positions[code] = {'shares': shares, 'cost': cost}

    print("========== 预测执行 ==========")
    for d in future_dates:
        print(f"\n--- 日期: {d} ---")
        account.trade(d)
        account.update_equity(d)
        
        # 打印当天的交易动作
        day_trades = [t for t in account.history if t['date'] == d]
        if not day_trades:
            print("  [静默] 无交易操作")
        else:
            for t in day_trades:
                action_str = "买入" if t['action'] == 'BUY' else "卖出"
                print(f"  [{action_str}] 代码: {t['code']}, 数量: {t['shares']}股, 价格: {t['price']:.2f}")

    print("\n========== 预测结束 ==========")
    print(f"最终资金可用余额: {account.cash:.2f}")
    if account.positions:
        print("最终预测持仓:")
        for code, pos in account.positions.items():
            print(f"  {code}: {pos['shares']}股")
    else:
        print("最终预测持仓: 空仓")
        
    # 保存预测结果 (简化保存，写入当前目录)
    with open("predict_history.json", "w", encoding="utf-8") as f:
        json.dump(account.history, f, ensure_ascii=False, indent=2)
    print("\n[完成] 预测结果及详细流水已保存在 predict_history.json 中。")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--weights', default='best_inferred_weights.json', help='拟合出的最佳权重文件')
    parser.add_argument('--stats', default='real_daily_stats_template.csv', help='真实历史每日状态文件')
    parser.add_argument('--days', type=int, default=7, help='预测未来的天数')
    args = parser.parse_args()
    
    run_prediction(args.weights, args.stats, args.days)
