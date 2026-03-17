"""
run_factor_mining.py — 因子挖矿演示（全市场）

两阶段：
  1. 选股因子  — 在截面日按因子值过滤，随机保留 15%~35%
  2. 信号因子  — 逐日计算横截面分位排名，驱动买入/卖出
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
    max_screen_factors=5,
    max_signal_factors=7,
    start_date='2025-12-01',
    end_date='2026-03-14',
    initial_cash=1_000_000,
    warmup_days=90,
    random_seed=None,
    top_n_stocks=5,
)

if 'error' in result and 'screen_factors' not in result:
    print(f'【错误】 {result["error"]}')
    sys.exit(1)

# ── 本次挖矿战绩 ─────────────────────────────────────────────────────────────
from datetime import datetime
sep = '='*60
print(f'\n{sep}')
print('【本次挖矿战绩】')
print(sep)
if result.get('backtest'):
    bt = result['backtest']
    tl = result.get('trade_log', [])
    n_buy  = sum(1 for t in tl if t['action'] == 'BUY')
    n_sell = sum(1 for t in tl if 'SELL' in t['action'])
    ret    = bt['total_return_pct']
    ann    = bt['annualized_return_pct']
    dd     = bt['max_drawdown_pct']
    ret_flag  = '▲' if ret >= 0 else '▼'
    ann_flag  = '▲' if ann >= 0 else '▼'
    print(f'  挖矿日期:   {datetime.today().strftime("%Y-%m-%d")}')
    print(f'  回测区间:   {bt["start_date"]}  →  {bt["end_date"]}（{bt["trading_days"]} 交易日）')
    print(f'  初始资金:   {bt["initial_cash"]:>14,.0f} 元')
    print(f'  期末资金:   {bt["final_value"]:>14,.2f} 元')
    print(f'  总收益率:   {ret_flag} {abs(ret):>10.4f} %')
    print(f'  年化收益率: {ann_flag} {abs(ann):>10.4f} %')
    print(f'  最大回撤:   ▼ {dd:>10.4f} %')
    print(f'  夏普比率:     {bt["sharpe_ratio"]:>10.4f}')
    print(f'  交易笔数:   买入 {n_buy} 笔 / 卖出 {n_sell} 笔（共 {n_buy+n_sell} 笔）')

# ── 基准对比表 ────────────────────────────────────────────────────────────
benchmarks = result.get('benchmarks', [])
if benchmarks and result.get('backtest') and not any('error' in b and len(b) == 1 for b in benchmarks):
    bt = result['backtest']
    strat_ret = bt['total_return_pct']
    strat_ann = bt['annualized_return_pct']
    strat_dd  = bt['max_drawdown_pct']
    print(f'  {"─"*54}')
    print(f'  {"基准对比（同期）":<10}  {"总收益":>8}  {"年化收益":>8}  {"最大回撤":>8}  {"超额收益":>9}  {"信息比率":>8}')
    print(f'  {"─"*54}')
    ret_sym = '▲' if strat_ret >= 0 else '▼'
    ann_sym = '▲' if strat_ann >= 0 else '▼'
    print(f'  {"策略本身":<10}  {ret_sym}{abs(strat_ret):>7.2f}%  {ann_sym}{abs(strat_ann):>7.2f}%  ▼{strat_dd:>7.2f}%  {"—":>9}  {"—":>8}')
    for b in benchmarks:
        if 'error' in b:
            print(f'  {b.get("name", b.get("code", "?")):<10}  {"数据不足":>38}')
            continue
        b_ret  = b['total_return_pct']
        b_ann  = b['annualized_return_pct']
        b_dd   = b['max_drawdown_pct']
        exc    = b['excess_return_pct']
        ir     = b['information_ratio']
        rs = '▲' if b_ret >= 0 else '▼'
        as_ = '▲' if b_ann >= 0 else '▼'
        es = '▲' if exc >= 0 else '▼'
        print(f'  {b["name"]:<10}  {rs}{abs(b_ret):>7.2f}%  {as_}{abs(b_ann):>7.2f}%  ▼{abs(b_dd):>7.2f}%  {es}{abs(exc):>8.2f}%  {ir:>8.2f}')
    print(f'  {"─"*54}')
print(sep)

# ── 选股因子 ─────────────────────────────────────────────────────────────────
print(f'\n【选股因子】  k = {result["screen_k"]}（截面日静态过滤）')
for name in result['screen_factors']:
    pct  = result['screen_top_pcts'].get(name, 0)
    desc = result['factor_descriptions'].get(name, '')
    print(f'  {name}  保留前{int(pct*100)}%  —  {desc}')

# ── 信号因子 ─────────────────────────────────────────────────────────────────
sc = result['signal_config']
print(f'\n【交易信号因子】  k = {result["signal_k"]}（逐日横截面排名驱动买卖）')
print(f'  买入阈值: 综合排名 >= {sc["buy_thresh"]}')
print(f'  卖出阈值: 综合排名 <= {sc["sell_thresh"]}')
for name in result['signal_factors']:
    desc = result['factor_descriptions'].get(name, '')
    print(f'  {name}  —  {desc}')

# ── 选股过滤过程 ─────────────────────────────────────────────────────────────
print()
if result.get('filter_log'):
    print('【选股过滤过程】')
    for step in result['filter_log']:
        status  = step['status']
        pct_str = f'保留前{int(step.get("top_pct", 0)*100)}%'
        if status == 'ok':
            print(f'  {step["factor"]}  {pct_str}  截面日={step["ref_date"]}  '
                  f'{step["before"]} → {step["after"]} 只  '
                  f'（实留 {step["kept"]}/{step["snapshot_size"]}）')
        else:
            print(f'  {step["factor"]}  {pct_str}  跳过（{status}）  {step["before"]} 只不变')

print(f'\n【最终入选】  {result["final_pool_count"]} 只')
if result['final_pool']:
    print(f'  {result["final_pool"]}')

# ── 回测结果 ─────────────────────────────────────────────────────────────────
if 'error' in result:
    print(f'\n【错误】 {result["error"]}')
elif 'backtest' in result:
    bt = result['backtest']
    print()
    print('【回测结果】（信号驱动买卖 / 等额资金分配）')
    print(f'  回测区间:   {bt["start_date"]}  →  {bt["end_date"]}')
    print(f'  交易天数:   {bt["trading_days"]} 日')
    print(f'  初始资金:   {bt["initial_cash"]:,.0f} 元')
    print(f'  期末资金:   {bt["final_value"]:,.2f} 元')
    print(f'  总收益率:   {bt["total_return_pct"]:+.4f} %')
    print(f'  年化收益率: {bt["annualized_return_pct"]:+.4f} %')
    print(f'  最大回撤:   {bt["max_drawdown_pct"]:.4f} %')
    print(f'  夏普比率:   {bt["sharpe_ratio"]:.4f}')
    ec  = bt['equity_curve']
    mid = len(ec) // 2
    print(f'  权益曲线（首/中/尾）:  [{ec[0]:,.0f}  ...  {ec[mid]:,.0f}  ...  {ec[-1]:,.0f}]')
    tl  = result.get('trade_log', [])
    print(f'  交易笔数:   买入 {sum(1 for t in tl if t["action"]=="BUY")} 笔 / '
          f'卖出 {sum(1 for t in tl if "SELL" in t["action"])} 笔')

# ── Top N 个股详情 ───────────────────────────────────────────────────────────
top_stocks = result.get('top_stocks', [])
sig_names  = result.get('signal_factors', [])
buy_thr    = sc['buy_thresh']
sell_thr   = sc['sell_thresh']

if top_stocks:
    print(f'\n{"="*60}')
    print(f'【Top {len(top_stocks)} 盈利个股详情（含每笔交易信号因子值）】')

    for rank_i, stock in enumerate(top_stocks, 1):
        code      = stock['code']
        total_pnl = stock['total_pnl']
        trades    = stock['trades']
        print(f'\n  #{rank_i}  {code}   累计盈亏: {total_pnl:+,.2f} 元')
        print(f'  {"─"*54}')

        for tr in trades:
            action       = tr['action']
            comp_rank    = tr.get('composite_rank')
            comp_str     = f'{comp_rank:.4f}' if comp_rank is not None else 'N/A'
            fv           = tr.get('factor_values', {})

            if action == 'BUY':
                flag = f'>= 买入阈值{buy_thr} ✓' if (comp_rank is not None and comp_rank >= buy_thr) else ''
                print(f'  [买入]  {tr["date"]}  价格={tr["price"]:.3f}  '
                      f'数量={tr["shares"]}股  金额={tr["amount"]:,.2f}元')
                print(f'         综合排名={comp_str}  {flag}')
                for sname in sig_names:
                    if sname in fv:
                        val  = fv[sname]['value']
                        rnk  = fv[sname]['rank']
                        flag2 = '✓' if rnk >= buy_thr else '✗'
                        print(f'           {sname}: 值={val:>10.4f}  排名={rnk:.4f}  (>={buy_thr} {flag2})')
                    else:
                        print(f'           {sname}: 数据缺失')

            else:
                label = '卖出' if action == 'SELL' else '强平'
                flag  = f'<= 卖出阈值{sell_thr} ✓' if (comp_rank is not None and comp_rank <= sell_thr) else '（强平）'
                print(f'  [{label}]  {tr["date"]}  价格={tr["price"]:.3f}  '
                      f'数量={tr["shares"]}股  回款={tr["amount"]:,.2f}元  '
                      f'持仓{tr.get("hold_days", "?")}日  '
                      f'盈亏={tr.get("pnl", 0):+,.2f}元 ({tr.get("pnl_pct", 0):+.2f}%)')
                print(f'         综合排名={comp_str}  {flag}')
                for sname in sig_names:
                    if sname in fv:
                        val  = fv[sname]['value']
                        rnk  = fv[sname]['rank']
                        flag2 = '✓' if rnk <= sell_thr else '✗'
                        print(f'           {sname}: 值={val:>10.4f}  排名={rnk:.4f}  (<={sell_thr} {flag2})')
                    else:
                        print(f'           {sname}: 数据缺失')


# ── 策略总结 ─────────────────────────────────────────────────────────────────
def _print_strategy_summary(r: dict) -> None:
    """根据本次因子挖矿结果动态生成详细策略说明。"""
    sc           = r['signal_config']
    screen_names = r['screen_factors']
    signal_names = r['signal_factors']
    descs        = r['factor_descriptions']
    top_pcts     = r['screen_top_pcts']
    filter_log   = r.get('filter_log', [])
    final_count  = r['final_pool_count']
    initial_pool = r['initial_pool']
    overlap      = set(screen_names) & set(signal_names)
    trade_log    = r.get('trade_log', [])

    sell_all   = [t for t in trade_log if 'SELL' in t['action']]
    force_sell = [t for t in trade_log if t['action'] == 'SELL(强平)']
    avg_hold   = round(
        sum(t.get('hold_days', 0) for t in sell_all) / max(len(sell_all), 1), 1
    )

    def direction_tag(desc):
        if '正向' in desc or '看涨' in desc: return '正向因子'
        if '反向' in desc or '看空' in desc: return '反向因子'
        return '条件因子'

    def core_desc(desc):
        return desc.split('。')[0] if '。' in desc else desc[:50]

    screen_pos  = sum(1 for n in screen_names if direction_tag(descs.get(n,'')) == '正向因子')
    screen_neg  = sum(1 for n in screen_names if direction_tag(descs.get(n,'')) == '反向因子')
    screen_cond = len(screen_names) - screen_pos - screen_neg
    sig_pos     = sum(1 for n in signal_names if direction_tag(descs.get(n,'')) == '正向因子')
    sig_neg     = sum(1 for n in signal_names if direction_tag(descs.get(n,'')) == '反向因子')
    sig_cond    = len(signal_names) - sig_pos - sig_neg

    sep = '='*60
    print(f'\n{sep}')
    print('【策略总结】')
    print(sep)

    # ── 一、策略概述
    print('\n▌ 一、策略概述')
    print(f'  本策略基于 WorldQuant《101 Formulaic Alphas》论文实现，')
    print(f'  采用"因子挖矿"框架，每次运行随机抽取因子并自动生成完整选股+交易策略。')
    print(f'  全流程分两个独立阶段：')
    print(f'    • 选股阶段 ({r["screen_k"]} 层)  — 截面日静态筛选，将全市场 {initial_pool} 只')
    print(f'      股票压缩至 {final_count} 只高质量候选标的')
    print(f'    • 交易阶段 ({r["signal_k"]} 个信号因子)  — 逐日动态跟踪，')
    print(f'      综合排名触及阈值时自动买入/卖出，不预设持仓期限')

    # ── 二、选股策略
    print(f'\n▌ 二、选股策略详解（{r["screen_k"]} 层串联过滤）')
    print(f'  核心逻辑: 多因子"与"关系过滤，每层在上一层结果中继续筛选，')
    print(f'    最终入选股票须同时通过所有层的因子检验。')
    print(f'  各层保留比例在 [15%, 35%] 内随机确定，控制每层筛选力度。')
    print()

    ok_steps = [s for s in filter_log if s['status'] == 'ok']
    for i, name in enumerate(screen_names, 1):
        pct  = top_pcts.get(name, 0)
        desc = descs.get(name, '')
        step = next((s for s in filter_log if s['factor'] == name), {})
        b, a = step.get('before', '?'), step.get('after', '?')
        tag  = direction_tag(desc)

        if '值越高→预期上涨' in desc:
            logic = f'保留因子值最高的前{int(pct*100)}% → 筛出当日强势股（该因子高值代表看涨）'
        elif '值越高→预期下跌' in desc:
            logic = f'保留因子值最高的前{int(pct*100)}% → 筛出超买最强股（反向因子，高值即过热）'
        elif '值为+1→预期上涨' in desc:
            logic = f'保留因子值最高的前{int(pct*100)}% → 筛出满足看涨条件（+1）的股票'
        else:
            logic = f'保留因子值最高的前{int(pct*100)}%'

        print(f'  第{i}层  {name}  [{tag}]  ({b} → {a} 只，保留前{int(pct*100)}%)')
        print(f'    含义: {core_desc(desc)}')
        print(f'    筛法: {logic}')
        print()

    type_parts = []
    if screen_pos:  type_parts.append(f'{screen_pos}个正向因子（趋势/动量/流动性）')
    if screen_neg:  type_parts.append(f'{screen_neg}个反向因子（反转/超买过滤）')
    if screen_cond: type_parts.append(f'{screen_cond}个条件因子（二值判断）')
    print(f'  本次选股因子组合: {" ＋ ".join(type_parts)}')
    print(f'  压缩漏斗: {" → ".join(str(s.get("before","?"))+"只" for s in ok_steps)} → {final_count}只')

    # ── 三、交易信号策略
    print(f'\n▌ 三、交易信号策略详解（{r["signal_k"]} 个因子驱动）')
    print(f'  每个交易日，对候选池所有股票：')
    print(f'    1. 计算每个信号因子在截面上的分位排名（0=最低，1=最高）')
    print(f'    2. 对各因子排名取平均，得到「综合排名」')
    print(f'    3. 综合排名 >= {sc["buy_thresh"]}  且  未持仓  →  买入（处于候选池前{int((1-sc["buy_thresh"])*100)}%）')
    print(f'    4. 综合排名 <= {sc["sell_thresh"]}  且  已持仓  →  卖出（跌入候选池后{int(sc["sell_thresh"]*100)}%）')
    print()

    for name in signal_names:
        desc = descs.get(name, '')
        tag  = direction_tag(desc)
        if '值越高→预期上涨' in desc:
            buy_interp  = f'排名≥{sc["buy_thresh"]} 表示该股在此因子上显著强势，动量/趋势积极'
            sell_interp = f'排名≤{sc["sell_thresh"]} 表示该股强势消退，信号转弱，及时离场'
        elif '值越高→预期下跌' in desc:
            buy_interp  = f'排名≥{sc["buy_thresh"]} 表示该股超买信号偏弱（反向），相对健康'
            sell_interp = f'排名≤{sc["sell_thresh"]} 表示该股超买信号极弱，可能正在发生反转下跌'
        elif '值为+1→预期上涨' in desc:
            buy_interp  = f'排名≥{sc["buy_thresh"]} 表示该股满足条件看涨信号（值接近+1）'
            sell_interp = f'排名≤{sc["sell_thresh"]} 表示条件信号转向看空（值接近-1）'
        else:
            buy_interp  = f'排名≥{sc["buy_thresh"]} 视为买入信号'
            sell_interp = f'排名≤{sc["sell_thresh"]} 视为卖出信号'

        print(f'  {name}  [{tag}]')
        print(f'    含义: {core_desc(desc)}')
        print(f'    买入解读: {buy_interp}')
        print(f'    卖出解读: {sell_interp}')
        print()

    sig_parts = []
    if sig_pos:  sig_parts.append(f'{sig_pos}个正向')
    if sig_neg:  sig_parts.append(f'{sig_neg}个反向')
    if sig_cond: sig_parts.append(f'{sig_cond}个条件')
    print(f'  信号因子组合: {" ＋ ".join(sig_parts)}，综合排名取均值平滑噪音')
    print(f'  买卖不对称设计: 买入阈值({sc["buy_thresh"]}) 高于中位，卖出阈值({sc["sell_thresh"]}) 低于中位，')
    print(f'    只在明确强势时入场，弱势明确时离场，中间区间持仓不动。')

    if overlap:
        print(f'\n  ★ 选股与信号共用因子: {", ".join(sorted(overlap))}')
        print(f'    这些因子在截面日用于静态选股，之后又在每个交易日持续跟踪信号，')
        print(f'    实现了"入池标准"与"持仓监控"的一致性。')

    # ── 四、持仓与风控
    print(f'\n▌ 四、持仓管理与风控')
    print(f'  仓位分配: 等额分配，单股预算 = 初始资金 ÷ {final_count}（候选池股数）')
    print(f'            每只股票独立决策，互不影响，最大持股数 = {final_count}')
    print(f'  平均持仓: {avg_hold} 日（含强平）')
    print(f'  持仓上限: 无杠杆，最大仓位100%（全部买入时）')
    if force_sell:
        fdate = force_sell[0]['date']
        print(f'  强平机制: {len(force_sell)} 只股票信号未触发卖出，在回测截止日 {fdate} 按收盘价强制清仓')
    print(f'  交易成本: 买入+卖出各收 0.1% 手续费（已计入回测）')
    print(f'  集中度: 最终持仓 {final_count} 只，', end='')
    if final_count == 1:
        print('单股极度集中，个股风险未分散，谨慎使用')
    elif final_count <= 5:
        print('高度集中，适合资金量小或对个股有深度研究时使用')
    elif final_count <= 20:
        print('适度集中，兼顾收益弹性与风险分散')
    else:
        print('较为分散，个股黑天鹅影响有限')

    # ── 五、综合评价
    print(f'\n▌ 五、综合评价')
    if r.get('backtest'):
        bt     = r['backtest']
        ret    = bt['total_return_pct']
        dd     = bt['max_drawdown_pct']
        sharpe = bt['sharpe_ratio']
        calmar = abs(ret / dd) if dd > 0 else float('inf')
        ann    = bt['annualized_return_pct']

        print(f'  样本内回测结果:  总收益 {ret:+.2f}%  | 年化 {ann:+.2f}%  | '
              f'最大回撤 {dd:.2f}%  | 夏普 {sharpe:.2f}  | Calmar {calmar:.2f}')
        print()

        # 各维度评价
        sharpe_eval = '★★★ 优秀' if sharpe>2 else ('★★ 良好' if sharpe>1 else ('★ 一般' if sharpe>0 else '✗ 亏损'))
        calmar_eval = '★★★ 优秀' if calmar>2 else ('★★ 良好' if calmar>1 else ('★ 一般' if calmar>0 else '✗ 亏损'))
        dd_eval     = '低风险' if dd<10 else ('中风险' if dd<25 else '高风险')
        conc_eval   = '极度集中' if final_count<=2 else ('高度集中' if final_count<=5 else '适度分散')

        print(f'  风险收益评价:')
        print(f'    夏普比率   {sharpe:.2f}  {sharpe_eval}  （衡量超额收益/波动比）')
        print(f'    Calmar比率 {calmar:.2f}  {calmar_eval}  （衡量收益/最大亏损比）')
        print(f'    最大回撤   {dd:.2f}%  {dd_eval}')
        print(f'    持仓集中度 {final_count}只  {conc_eval}')
        print()

        # 基准对比
        benchmarks = r.get('benchmarks', [])
        valid_bm = [b for b in benchmarks if 'error' not in b]
        if valid_bm:
            print(f'  基准对比（超额收益 / 信息比率）:')
            for b in valid_bm:
                exc = b['excess_return_pct']
                ir  = b['information_ratio']
                exc_sym = '▲' if exc >= 0 else '▼'
                ir_eval = '优秀' if ir > 1 else ('良好' if ir > 0.5 else ('一般' if ir > 0 else '跑输'))
                print(f'    vs {b["name"]:<6}  超额 {exc_sym}{abs(exc):.2f}%  IR={ir:.2f}  ({ir_eval})')
            print()

        print(f'  注意事项:')
        print(f'    ① 以上为样本内回测，因子与参数均由随机生成，存在过拟合风险')
        print(f'    ② 实盘需注意流动性：候选池越小，冲击成本越高')
        print(f'    ③ 信号因子在候选池截面内计算排名，候选池过小时排名区分度下降')
        print(f'    ④ 本策略仅为研究框架演示，不构成投资建议')


_print_strategy_summary(result)

print('\n' + '='*60)
