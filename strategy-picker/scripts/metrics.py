"""
metrics.py - 性能指标计算模块

功能：
1. 回测性能指标计算
2. 风险指标计算

设计原则：
- 函数功能单一、最小粒度
- 基于权益曲线和交易记录计算
"""

from typing import List, Dict, Tuple


def get_max_drawdown(equity_curve: List[float]) -> Tuple[float, int, int]:
    """计算最大回撤 (最大回撤比例, 最高点索引, 最低点索引)"""
    if not equity_curve:
        return 0, 0, 0
    
    max_dd = 0
    max_idx, min_idx = 0, 0
    peak = equity_curve[0]
    peak_idx = 0
    
    for i, value in enumerate(equity_curve):
        if value > peak:
            peak, peak_idx = value, i
        
        dd = (peak - value) / peak if peak > 0 else 0
        if dd > max_dd:
            max_dd, max_idx, min_idx = dd, i, peak_idx
    
    return max_dd, max_idx, min_idx


def get_max_drawdown_pct(equity_curve: List[float]) -> float:
    """获取最大回撤百分比"""
    dd, _, _ = get_max_drawdown(equity_curve)
    return dd


def get_annualized_return(total_return: float, days: int) -> float:
    """计算年化收益率"""
    if days <= 0:
        return 0
    years = days / 252
    if years <= 0:
        return 0
    return ((1 + total_return) ** (1 / years) - 1)


def get_total_return(initial_value: float, final_value: float) -> float:
    """计算总收益率"""
    if initial_value <= 0:
        return 0
    return (final_value - initial_value) / initial_value


def get_sharpe_ratio(equity_curve: List[float], risk_free_rate: float = 0.03) -> float:
    """计算夏普比率"""
    if len(equity_curve) < 2:
        return 0
    
    returns = []
    for i in range(1, len(equity_curve)):
        if equity_curve[i-1] > 0:
            ret = (equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1]
            returns.append(ret)
    
    if not returns:
        return 0
    
    avg_return = sum(returns) / len(returns)
    variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
    std_dev = variance ** 0.5
    
    if std_dev == 0:
        return 0
    
    daily_rf = risk_free_rate / 252
    sharpe = (avg_return - daily_rf) / std_dev * (252 ** 0.5)
    return sharpe


def get_win_rate(trades: List[Dict]) -> float:
    """计算胜率 (0-100)"""
    if not trades:
        return 0
    wins = sum(1 for t in trades if t.get('profit', 0) > 0)
    return (wins / len(trades)) * 100


def get_profit_loss_ratio(trades: List[Dict]) -> float:
    """计算盈亏比"""
    profits = [t['profit'] for t in trades if t.get('profit', 0) > 0]
    losses = [abs(t['profit']) for t in trades if t.get('profit', 0) < 0]
    
    avg_profit = sum(profits) / len(profits) if profits else 0
    avg_loss = sum(losses) / len(losses) if losses else 0
    
    if avg_loss == 0:
        return float('inf') if avg_profit > 0 else 0
    return avg_profit / avg_loss


def get_calmar_ratio(equity_curve: List[float], days: int) -> float:
    """计算卡尔玛比率"""
    if len(equity_curve) < 2:
        return 0
    
    total_return = get_total_return(equity_curve[0], equity_curve[-1])
    annualized = get_annualized_return(total_return, days)
    max_dd = get_max_drawdown_pct(equity_curve)
    
    if max_dd == 0:
        return 0
    return annualized / max_dd


def get_volatility(equity_curve: List[float]) -> float:
    """计算收益波动率（年化）"""
    if len(equity_curve) < 2:
        return 0
    
    returns = []
    for i in range(1, len(equity_curve)):
        if equity_curve[i-1] > 0:
            ret = (equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1]
            returns.append(ret)
    
    if not returns:
        return 0
    
    variance = sum((r - sum(returns)/len(returns)) ** 2 for r in returns) / len(returns)
    daily_vol = variance ** 0.5
    return daily_vol * (252 ** 0.5)


def get_trade_stats(trades: List[Dict]) -> Dict:
    """获取交易统计信息"""
    if not trades:
        return {
            'total_trades': 0, 'wins': 0, 'losses': 0, 'win_rate': 0,
            'profit_loss_ratio': 0, 'total_profit': 0, 'total_loss': 0,
            'avg_profit': 0, 'avg_loss': 0,
        }
    
    wins = [t for t in trades if t.get('profit', 0) > 0]
    losses = [t for t in trades if t.get('profit', 0) < 0]
    
    return {
        'total_trades': len(trades),
        'wins': len(wins),
        'losses': len(losses),
        'win_rate': get_win_rate(trades),
        'profit_loss_ratio': get_profit_loss_ratio(trades),
        'total_profit': sum(t['profit'] for t in wins),
        'total_loss': sum(t['profit'] for t in losses),
        'avg_profit': sum(t['profit'] for t in wins) / len(wins) if wins else 0,
        'avg_loss': sum(t['profit'] for t in losses) / len(losses) if losses else 0,
    }


def generate_report(equity_curve: List[float], trades: List[Dict], initial_cash: float, days: int) -> Dict:
    """生成完整的回测报告"""
    final_value = equity_curve[-1] if equity_curve else initial_cash
    total_return = get_total_return(initial_cash, final_value)
    
    return {
        'initial_cash': initial_cash,
        'final_value': final_value,
        'total_return': total_return,
        'total_return_pct': total_return * 100,
        'annualized_return': get_annualized_return(total_return, days),
        'annualized_return_pct': get_annualized_return(total_return, days) * 100,
        'max_drawdown': get_max_drawdown_pct(equity_curve),
        'max_drawdown_pct': get_max_drawdown_pct(equity_curve) * 100,
        'sharpe_ratio': get_sharpe_ratio(equity_curve),
        'calmar_ratio': get_calmar_ratio(equity_curve, days),
        'volatility': get_volatility(equity_curve),
        'trading_days': days,
        'trade_stats': get_trade_stats(trades),
    }
