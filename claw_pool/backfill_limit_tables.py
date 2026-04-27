#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
根据现有 `daily_kline` / `stock_basic` 数据，回填本地涨跌停相关表。

说明：
- 这是在官方 `stock_limit` / `daily_limit_list` / `daily_bomb_list` 缺失时的本地推导版本
- 结果可供回测器优先按标准表结构读取，但仍不等同于交易所级别的精确盘口数据
"""

import argparse
import sqlite3
from datetime import datetime
from typing import Optional

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

    upper_name = (name or "").upper()
    if code.endswith(".BJ"):
        return 0.30
    if code.startswith(("300", "301", "688", "689")):
        return 0.20
    if upper_name.startswith("ST") or upper_name.startswith("*ST"):
        return 0.05
    return 0.10


def approx_equal(a: float, b: float) -> bool:
    tolerance = max(0.01, abs(b) * 0.001)
    return abs(float(a) - float(b)) <= tolerance


def fetch_daily_rows(conn: sqlite3.Connection, start_date: Optional[str], end_date: Optional[str]):
    sql = """
    SELECT
        k.date,
        k.code,
        COALESCE(b.name, k.code) AS name,
        COALESCE(b.list_date, '') AS list_date,
        k.open,
        k.high,
        k.low,
        k.close,
        k.volume,
        k.amount,
        k.pre_close,
        k.pctChg
    FROM daily_kline k
    LEFT JOIN stock_basic b ON b.ts_code = k.code
    """
    conditions = []
    params = []
    if start_date:
        conditions.append("k.date >= ?")
        params.append(start_date)
    if end_date:
        conditions.append("k.date <= ?")
        params.append(end_date)
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY k.code, k.date"
    return conn.execute(sql, params).fetchall()


def main():
    parser = argparse.ArgumentParser(description="回填本地涨跌停相关表")
    parser.add_argument("--start-date", help="开始日期 YYYY-MM-DD")
    parser.add_argument("--end-date", help="结束日期 YYYY-MM-DD")
    parser.add_argument("--truncate", action="store_true", help="回填前清空三张表")
    args = parser.parse_args()

    conn = get_db_connection()
    cur = conn.cursor()

    if args.truncate:
        for table in ("stock_limit", "daily_limit_list", "daily_bomb_list"):
            cur.execute(f"DELETE FROM {table}")
        conn.commit()

    rows = fetch_daily_rows(conn, args.start_date, args.end_date)
    stock_limit_rows = []
    daily_limit_rows = []
    daily_bomb_rows = []
    streak_map = {}

    for row in rows:
        (
            trade_date,
            code,
            name,
            list_date,
            open_price,
            high_price,
            low_price,
            close_price,
            volume,
            amount,
            pre_close,
            pct_chg,
        ) = row

        if pre_close is None or float(pre_close) <= 0:
            streak_map[code] = 0
            continue

        limit_pct = infer_limit_pct(code, name, list_date, trade_date)
        if limit_pct is None:
            streak_map[code] = 0
            continue

        up_limit = round(float(pre_close) * (1 + limit_pct), 2)
        down_limit = round(float(pre_close) * (1 - limit_pct), 2)

        stock_limit_rows.append((
            trade_date,
            code,
            float(pre_close),
            up_limit,
            down_limit,
        ))

        is_up_close = approx_equal(close_price, up_limit)
        is_down_close = approx_equal(close_price, down_limit)
        touched_up = float(high_price) >= up_limit - max(0.01, up_limit * 0.001)
        touched_down = float(low_price) <= down_limit + max(0.01, down_limit * 0.001)

        if is_up_close:
            streak_map[code] = streak_map.get(code, 0) + 1
            daily_limit_rows.append((
                trade_date,
                code,
                name,
                "U",
                up_limit,
                float(pct_chg or 0),
                float(volume or 0),
                float(amount or 0),
                streak_map[code],
                "",
            ))
        else:
            streak_map[code] = 0

        if is_down_close:
            daily_limit_rows.append((
                trade_date,
                code,
                name,
                "D",
                down_limit,
                float(pct_chg or 0),
                float(volume or 0),
                float(amount or 0),
                0,
                "",
            ))

        if touched_up and not is_up_close:
            daily_bomb_rows.append((
                trade_date,
                code,
                name,
                "U",
                up_limit,
                float(pct_chg or 0),
                float(volume or 0),
                float(amount or 0),
                "",
            ))

        if touched_down and not is_down_close:
            daily_bomb_rows.append((
                trade_date,
                code,
                name,
                "D",
                down_limit,
                float(pct_chg or 0),
                float(volume or 0),
                float(amount or 0),
                "",
            ))

    cur.executemany(
        """
        INSERT OR REPLACE INTO stock_limit(trade_date, ts_code, pre_close, up_limit, down_limit)
        VALUES (?, ?, ?, ?, ?)
        """,
        stock_limit_rows,
    )
    cur.executemany(
        """
        INSERT OR REPLACE INTO daily_limit_list(
            trade_date, ts_code, name, limit_type, limit_price, pct_chg, volume, amount, limit_streak, sector
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        daily_limit_rows,
    )
    cur.executemany(
        """
        INSERT OR REPLACE INTO daily_bomb_list(
            trade_date, ts_code, name, bomb_type, limit_price, pct_chg, volume, amount, sector
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        daily_bomb_rows,
    )
    conn.commit()

    print(f"stock_limit: {len(stock_limit_rows)}")
    print(f"daily_limit_list: {len(daily_limit_rows)}")
    print(f"daily_bomb_list: {len(daily_bomb_rows)}")
    conn.close()


if __name__ == "__main__":
    main()
