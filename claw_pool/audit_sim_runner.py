#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
对 claw_pool_sim_runner 的输出结果做快速审计。

校验内容：
1. 买入数量是否为 100 股整数倍
2. 成交价是否等于当日开盘价
3. 是否误买入一字涨停 / 误卖出一字跌停
4. 数据库中是否存在大幅价格跳变样本
5. T+1 违规：当日买入的股票当日卖出
6. 停牌日交易：成交量为 0 的日期产生了买卖
7. ST/创业板/科创板/北交所涨跌幅阈值是否正确区分
8. 收盘价超出理论涨跌停价范围（数据异常）
9. 卖出股数超过持仓（空卖）
10. 佣金最低 5 元检查
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


def _get_stock_info(cur, code: str):
    """查询股票基础信息，返回 (name, list_date)"""
    row = cur.execute(
        "SELECT name, list_date FROM stock_basic WHERE ts_code = ? LIMIT 1",
        (code,),
    ).fetchone()
    return (row[0] if row else "", row[1] if row else "")


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

        # 按账户追踪持仓和当日买入记录，用于 T+1 和空卖检查
        positions = {}  # code -> shares
        daily_buys = {}  # (date, code) -> True

        for row in rows:
            result["trade_count"] += 1
            code = row["股票代码"]
            trade_date = row["日期"]
            action = row["动作"]
            shares = int(row["数量"])
            price = float(row["价格"])
            amount = shares * price

            # --- 检查 1: 买入股数 100 整数倍 ---
            if action == "BUY" and shares % 100 != 0:
                result["issues"].append({
                    "type": "buy_lot_not_100",
                    "file": os.path.basename(trade_file),
                    "row": row,
                })

            # --- 检查 5: T+1 违规 ---
            if action == "BUY":
                daily_buys[(trade_date, code)] = True
                positions[code] = positions.get(code, 0) + shares
            if action == "SELL":
                if (trade_date, code) in daily_buys:
                    result["issues"].append({
                        "type": "t_plus_1_violation",
                        "file": os.path.basename(trade_file),
                        "row": row,
                    })

            # --- 检查 9: 卖出股数超过持仓（空卖） ---
            if action == "SELL":
                held = positions.get(code, 0)
                if shares > held:
                    result["issues"].append({
                        "type": "oversell_no_position",
                        "file": os.path.basename(trade_file),
                        "row": row,
                        "held_shares": held,
                    })
                positions[code] = max(0, held - shares)

            # --- 检查 10: 佣金最低 5 元 ---
            fee = amount * 0.0003
            if fee < 5.0:
                result["issues"].append({
                    "type": "commission_below_minimum",
                    "file": os.path.basename(trade_file),
                    "row": row,
                    "calculated_fee": round(fee, 2),
                    "minimum_fee": 5.0,
                })

            market_row = cur.execute(
                "SELECT open, high, low, close, pre_close, volume FROM daily_kline WHERE code = ? AND date = ?",
                (code, trade_date),
            ).fetchone()
            if not market_row:
                result["issues"].append({
                    "type": "missing_kline",
                    "file": os.path.basename(trade_file),
                    "row": row,
                })
                continue

            open_price, high_price, low_price, close_price, pre_close, volume = market_row

            # --- 检查 2: 成交价是否等于当日开盘价 ---
            if abs(price - float(open_price)) > 1e-6:
                result["issues"].append({
                    "type": "trade_price_not_open",
                    "file": os.path.basename(trade_file),
                    "row": row,
                    "market_open": open_price,
                })

            # --- 检查 6: 停牌日交易（成交量为 0） ---
            if volume is not None and float(volume) <= 0:
                result["issues"].append({
                    "type": "trade_on_suspended_day",
                    "file": os.path.basename(trade_file),
                    "row": row,
                })

            if pre_close:
                stock_name, list_date = _get_stock_info(cur, code)
                up_limit = resolve_limit_price(cur, code, trade_date, pre_close, "up", stock_name, list_date)
                down_limit = resolve_limit_price(cur, code, trade_date, pre_close, "down", stock_name, list_date)

                if up_limit is not None and down_limit is not None:
                    market_dict = {
                        "open": open_price,
                        "high": high_price,
                        "low": low_price,
                        "close": close_price,
                    }

                    # --- 检查 3: 一字涨停买入 / 一字跌停卖出 ---
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

                    # --- 检查 8: 收盘价超出理论涨跌停价范围（数据异常） ---
                    close_f = float(close_price)
                    tolerance = max(0.01, abs(up_limit) * 0.002)
                    if close_f > up_limit + tolerance or close_f < down_limit - tolerance:
                        result["issues"].append({
                            "type": "close_price_out_of_limit_range",
                            "file": os.path.basename(trade_file),
                            "row": row,
                            "close": close_f,
                            "up_limit": up_limit,
                            "down_limit": down_limit,
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

    # 检查 4: 单日价格跳变 >30%
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

    # 检查 7: 涨跌幅阈值分布统计（按板块）
    limit_pct_distribution = {}
    for label, prefix_cond in (
        ("主板_10pct", "code NOT LIKE '300%' AND code NOT LIKE '301%' AND code NOT LIKE '688%' AND code NOT LIKE '689%' AND code NOT LIKE '%.BJ'"),
        ("创业板_20pct", "code LIKE '300%' OR code LIKE '301%'"),
        ("科创板_20pct", "code LIKE '688%' OR code LIKE '689%'"),
    ):
        row = cur.execute(
            f"SELECT COUNT(*) FROM daily_kline WHERE ({prefix_cond}) AND pre_close > 0 AND ABS(close/pre_close - 1) > 0.105"
        ).fetchone()
        limit_pct_distribution[label + "_exceed_10pct"] = row[0] if row else 0

    # 检查 8: 收盘价超出涨跌停价的全局扫描
    close_out_of_range = cur.execute(
        """
        SELECT k.code, k.date, k.close, k.pre_close, sl.up_limit, sl.down_limit
        FROM daily_kline k
        JOIN stock_limit sl ON k.code = sl.ts_code AND REPLACE(k.date, '-', '') = REPLACE(sl.trade_date, '-', '')
        WHERE sl.up_limit > 0 AND sl.down_limit > 0
          AND (k.close > sl.up_limit * 1.002 OR k.close < sl.down_limit * 0.998)
        LIMIT ?
        """,
        (sample_limit,),
    ).fetchall()

    # 停牌日有成交记录的异常
    suspended_with_trades = cur.execute(
        """
        SELECT code, date, volume, close
        FROM daily_kline
        WHERE (volume IS NULL OR volume = 0)
          AND (close IS NOT NULL AND close > 0)
        LIMIT ?
        """,
        (sample_limit,),
    ).fetchall()

    result = {
        "table_counts": table_counts,
        "price_gap_samples": price_gap_rows,
        "limit_pct_distribution": limit_pct_distribution,
        "close_out_of_range_samples": close_out_of_range,
        "suspended_with_price_samples": suspended_with_trades,
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
