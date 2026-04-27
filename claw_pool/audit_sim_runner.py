#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
对 claw_pool_sim_runner 的输出结果做快速审计。

校验内容：
1. 买入数量是否为 100 股整数倍
2. 成交价是否等于当日开盘价
3. 是否误买入一字涨停 / 误卖出一字跌停
4. 数据库中是否存在大幅价格跳变样本
"""

import os
import csv
import glob
import json
import argparse
import sqlite3
from datetime import datetime

DB_PATH = r"C:\Users\admin\AppData\Local\Temp\BitSoulStockSkill\data.db"


def get_db_connection():
    return sqlite3.connect(DB_PATH)


def infer_limit_pct(code: str, name: str, list_date: str, trade_date: str):
    if list_date:
        try:
            listed_days = (datetime.strptime(trade_date, "%Y-%m-%d") - datetime.strptime(list_date, "%Y-%m-%d")).days
            if listed_days < 5:
                return None
        except ValueError:
            pass

    if code.endswith(".BJ"):
        return 0.30
    if code.startswith(("300", "301", "688", "689")):
        return 0.20
    if (name or "").upper().startswith(("ST", "*ST")):
        return 0.05
    return 0.10


def resolve_limit_price(cur, code: str, trade_date: str, pre_close: float, direction: str, name: str, list_date: str):
    row = cur.execute(
        """
        SELECT up_limit, down_limit
        FROM stock_limit
        WHERE ts_code = ? AND REPLACE(trade_date, '-', '') = ?
        LIMIT 1
        """,
        (code, trade_date.replace("-", "")),
    ).fetchone()
    if row:
        return float(row[0] if direction == "up" else row[1])

    limit_pct = infer_limit_pct(code, name, list_date, trade_date)
    if limit_pct is None:
        return None
    factor = 1 + limit_pct if direction == "up" else 1 - limit_pct
    return round(float(pre_close) * factor, 2)


def is_one_word_limit(row, limit_price):
    tolerance = max(0.01, abs(limit_price) * 0.001)
    prices = [float(row[k]) for k in ("open", "high", "low", "close")]
    return all(abs(price - limit_price) <= tolerance for price in prices)


def audit_ranking_dir(ranking_dir: str):
    conn = get_db_connection()
    cur = conn.cursor()
    trade_files = glob.glob(os.path.join(ranking_dir, "trades", "account_*_trades.csv"))

    result = {
        "ranking_dir": ranking_dir,
        "trade_file_count": len(trade_files),
        "trade_count": 0,
        "issues": [],
    }

    for trade_file in trade_files:
        with open(trade_file, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        for row in rows:
            result["trade_count"] += 1
            code = row["股票代码"]
            trade_date = row["日期"]
            action = row["动作"]
            shares = int(row["数量"])
            price = float(row["价格"])

            if action == "BUY" and shares % 100 != 0:
                result["issues"].append({
                    "type": "buy_lot_not_100",
                    "file": os.path.basename(trade_file),
                    "row": row,
                })

            market_row = cur.execute(
                "SELECT open, high, low, close, pre_close FROM daily_kline WHERE code = ? AND date = ?",
                (code, trade_date),
            ).fetchone()
            if not market_row:
                result["issues"].append({
                    "type": "missing_kline",
                    "file": os.path.basename(trade_file),
                    "row": row,
                })
                continue

            open_price, high_price, low_price, close_price, pre_close = market_row
            if abs(price - float(open_price)) > 1e-6:
                result["issues"].append({
                    "type": "trade_price_not_open",
                    "file": os.path.basename(trade_file),
                    "row": row,
                    "market_open": open_price,
                })

            if pre_close:
                info_row = cur.execute(
                    "SELECT name, list_date FROM stock_basic WHERE ts_code = ?",
                    (code,),
                ).fetchone()
                stock_name = info_row[0] if info_row else ""
                list_date = info_row[1] if info_row else ""
                up_limit = resolve_limit_price(cur, code, trade_date, pre_close, "up", stock_name, list_date)
                down_limit = resolve_limit_price(cur, code, trade_date, pre_close, "down", stock_name, list_date)
                if up_limit is not None and down_limit is not None:
                    market_dict = {
                        "open": open_price,
                        "high": high_price,
                        "low": low_price,
                        "close": close_price,
                    }
                    if action == "BUY" and is_one_word_limit(market_dict, up_limit):
                        result["issues"].append({
                            "type": "buy_on_one_word_up_limit",
                            "file": os.path.basename(trade_file),
                            "row": row,
                        })
                    if action == "SELL" and is_one_word_limit(market_dict, down_limit):
                        result["issues"].append({
                            "type": "sell_on_one_word_down_limit",
                            "file": os.path.basename(trade_file),
                            "row": row,
                        })

    result["issue_count"] = len(result["issues"])
    conn.close()
    return result


def scan_db_anomalies(sample_limit: int = 20):
    conn = get_db_connection()
    cur = conn.cursor()

    table_counts = {}
    for table, date_col in (
        ("daily_kline", "date"),
        ("daily_basic", "trade_date"),
        ("stock_limit", "trade_date"),
        ("daily_limit_list", "trade_date"),
        ("daily_bomb_list", "trade_date"),
    ):
        table_counts[table] = cur.execute(
            f"SELECT MIN({date_col}), MAX({date_col}), COUNT(*) FROM {table}"
        ).fetchone()

    price_gap_rows = cur.execute(
        """
        SELECT code, date, close, pre_close, pctChg
        FROM daily_kline
        WHERE pre_close IS NOT NULL
          AND pre_close != 0
          AND ABS(close / pre_close - 1) > 0.3
        ORDER BY ABS(close / pre_close - 1) DESC
        LIMIT ?
        """,
        (sample_limit,),
    ).fetchall()

    result = {
        "table_counts": table_counts,
        "price_gap_samples": price_gap_rows,
    }
    conn.close()
    return result


def main():
    parser = argparse.ArgumentParser(description="审计 claw_pool 模拟结果")
    parser.add_argument("--ranking-dir", required=True, help="要审计的 ranking_xxx 目录")
    parser.add_argument("--sample-limit", type=int, default=20, help="异常样本输出数量")
    args = parser.parse_args()

    report = {
        "trade_audit": audit_ranking_dir(args.ranking_dir),
        "db_anomalies": scan_db_anomalies(args.sample_limit),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
