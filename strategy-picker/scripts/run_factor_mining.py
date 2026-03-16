"""
run_factor_mining.py — 因子挖矿演示（全市场）
"""
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stock_api import StockApi

api = StockApi()

# ── 股票池：全市场 ───────────────────────────────────────────────────────────
POOL = api.get_all_symbols()
print(f'股票池: {len(POOL)} 只（全市场）')

# ── 运行因子挖矿 ─────────────────────────────────────────────────────────────
print('\n' + '='*60)
print('开始因子挖矿...')
print('='*60)

result = api.random_alpha_backtest(
    codes=POOL,
    max_factors=5,             # 随机 1~5 个因子
    start_date='2025-12-01',
    end_date='2026-03-14',
    top_pct=0.25,
    initial_cash=1_000_000,
    warmup_days=90,
    random_seed=None,
)

# ── 打印结果 ─────────────────────────────────────────────────────────────────
print(f'\n【随机因子数量】  k = {result["random_k"]}')
print(f'【初始股票池】    {result["initial_pool"]} 只')
print()
print('【选中因子及说明】')
for name, desc in result['factor_descriptions'].items():
    print(f'  {name}  —  {desc}')
print()

if result.get('filter_log'):
    print('【过滤过程】')
    for step in result['filter_log']:
        status = step['status']
        if status == 'ok':
            print(f'  {step["factor"]}  截面日={step["ref_date"]}  '
                  f'{step["before"]} → {step["after"]} 只  '
                  f'（保留 {step["kept"]}/{step["snapshot_size"]}）')
        else:
            print(f'  {step["factor"]}  跳过（{status}）  {step["before"]} 只不变')
else:
    print('【过滤过程】  k=0，不执行过滤')

print()
print(f'【最终入选】  {result["final_pool_count"]} 只')
if result['final_pool']:
    print(f'  {result["final_pool"]}')

if 'error' in result:
    print(f'\n【错误】 {result["error"]}')
elif 'backtest' in result:
    bt = result['backtest']
    print()
    print('【回测结果】')
    print(f'  回测区间:   {bt["start_date"]}  →  {bt["end_date"]}')
    print(f'  交易天数:   {bt["trading_days"]} 日')
    print(f'  初始资金:   {bt["initial_cash"]:,.0f} 元')
    print(f'  期末资金:   {bt["final_value"]:,.2f} 元')
    print(f'  总收益率:   {bt["total_return_pct"]:+.4f} %')
    print(f'  年化收益率: {bt["annualized_return_pct"]:+.4f} %')
    print(f'  最大回撤:   {bt["max_drawdown_pct"]:.4f} %')
    print(f'  夏普比率:   {bt["sharpe_ratio"]:.4f}')
    print()
    ec = bt['equity_curve']
    mid = len(ec) // 2
    print(f'  权益曲线（首/中/尾）:')
    print(f'    [{ec[0]:,.0f}  ...  {ec[mid]:,.0f}  ...  {ec[-1]:,.0f}]')

print('\n' + '='*60)
