"""
backtest_tools.py - 回测工具模块

功能：
1. 交易模拟
2. 持仓管理
3. 组合价值计算

设计原则：
- 函数功能单一、最小粒度
- 纯函数，无副作用
"""

from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class Position:
    """持仓"""
    code: str
    shares: int
    entry_price: float
    entry_date: str
    hold_days: int = 0


def simulate_trade(action: str, price: float, quantity: int, fee_rate: float = 0.0003) -> Dict:
    """
    模拟单笔交易
    Returns: {'cost': 成本, 'fee': 手续费, 'net_proceeds': 净收款(卖出)}
    """
    action = action.upper()
    fee = price * quantity * fee_rate
    
    if action == 'BUY':
        cost = price * quantity * (1 + fee_rate)
        return {'cost': cost, 'fee': fee, 'net_proceeds': 0}
    else:
        net = price * quantity * (1 - fee_rate)
        return {'cost': 0, 'fee': fee, 'net_proceeds': net}


def calculate_trade_cost(action: str, price: float, quantity: int, fee_rate: float = 0.0003, slippage: float = 0.0) -> float:
    """计算交易成本（含滑点）"""
    if action.upper() == 'BUY':
        actual_price = price * (1 + slippage)
    else:
        actual_price = price * (1 - slippage)
    return actual_price * quantity * (1 + fee_rate)


def create_position(code: str, shares: int, price: float, date: str) -> Position:
    """创建持仓"""
    return Position(code=code, shares=shares, entry_price=price, entry_date=date, hold_days=0)


def update_position(position: Position, days: int = 1) -> Position:
    """更新持仓持有天数"""
    position.hold_days += days
    return position


def get_position_value(position: Position, current_price: float) -> float:
    """计算持仓市值"""
    return position.shares * current_price


def get_position_profit(position: Position, current_price: float) -> Tuple[float, float]:
    """计算持仓盈亏 (金额, 比例)"""
    profit = (current_price - position.entry_price) * position.shares
    profit_pct = (current_price - position.entry_price) / position.entry_price
    return profit, profit_pct


def calculate_portfolio_value(cash: float, positions: Dict[str, Position], prices: Dict[str, float]) -> float:
    """计算组合总价值"""
    position_value = sum(
        p.shares * prices.get(p.code, p.entry_price)
        for p in positions.values()
    )
    return cash + position_value


def get_portfolio_positions(positions: Dict[str, Position]) -> List[Dict]:
    """获取组合持仓详情"""
    return [
        {
            'code': p.code,
            'shares': p.shares,
            'entry_price': p.entry_price,
            'entry_date': p.entry_date,
            'hold_days': p.hold_days,
        }
        for p in positions.values()
    ]


def build_equity_curve(daily_values: List[Tuple[str, float]]) -> List[float]:
    """构建权益曲线"""
    return [value for _, value in daily_values]


def calculate_daily_returns(equity_curve: List[float]) -> List[float]:
    """计算日收益率"""
    if len(equity_curve) < 2:
        return []
    return [
        (equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1]
        for i in range(1, len(equity_curve))
        if equity_curve[i-1] > 0
    ]


def should_buy(current_price: float, ma_short: float, ma_long: float, rsi: float = 50, rsi_oversold: float = 30) -> bool:
    """买入信号判断（MA金叉 + RSI超卖）"""
    return ma_short > ma_long and rsi < rsi_oversold


def should_sell(current_price: float, ma_short: float, ma_long: float, rsi: float = 50, rsi_overbought: float = 70) -> bool:
    """卖出信号判断（MA死叉 / RSI超买）"""
    return ma_short < ma_long or rsi > rsi_overbought


def calculate_drawdown(equity_curve: List[float]) -> List[float]:
    """计算回撤序列"""
    if not equity_curve:
        return []
    
    drawdowns = []
    peak = equity_curve[0]
    
    for value in equity_curve:
        if value > peak:
            peak = value
        dd = (peak - value) / peak if peak > 0 else 0
        drawdowns.append(dd)
    
    return drawdowns


@dataclass
class TradeResult:
    """交易结果"""
    success: bool
    code: str
    action: str
    price: float
    quantity: int
    cost: float = 0.0
    fee: float = 0.0
    net_proceeds: float = 0.0
    reason: str = ""
    position: Position = None


def buy(cash: float, positions: Dict[str, Position], code: str, price: float, quantity: int, date: str, fee_rate: float = 0.0003) -> Tuple[float, Dict[str, Position], TradeResult]:
    """
    买入股票
    
    Args:
        cash: 当前现金
        positions: 持仓字典 {code: Position}
        code: 股票代码
        price: 买入价格
        quantity: 买入数量
        date: 交易日期
        fee_rate: 手续费率
    
    Returns:
        (更新后的现金, 更新后的持仓字典, 交易结果)
    """
    trade = simulate_trade('BUY', price, quantity, fee_rate)
    cost = trade['cost']
    
    if cash < cost:
        return cash, positions, TradeResult(
            success=False,
            code=code,
            action='BUY',
            price=price,
            quantity=quantity,
            reason='资金不足',
        )
    
    new_cash = cash - cost
    
    if code in positions:
        pos = positions[code]
        total_cost = pos.entry_price * pos.shares + cost
        new_shares = pos.shares + quantity
        new_entry_price = total_cost / new_shares
        positions[code] = Position(
            code=code,
            shares=new_shares,
            entry_price=new_entry_price,
            entry_date=pos.entry_date,
            hold_days=0,
        )
    else:
        positions[code] = Position(
            code=code,
            shares=quantity,
            entry_price=price,
            entry_date=date,
            hold_days=0,
        )
    
    return new_cash, positions, TradeResult(
        success=True,
        code=code,
        action='BUY',
        price=price,
        quantity=quantity,
        cost=cost,
        fee=trade['fee'],
        position=positions[code],
    )


def sell(cash: float, positions: Dict[str, Position], code: str, price: float, quantity: int, fee_rate: float = 0.0003) -> Tuple[float, Dict[str, Position], TradeResult]:
    """
    卖出股票
    
    Args:
        cash: 当前现金
        positions: 持仓字典 {code: Position}
        code: 股票代码
        price: 卖出价格
        quantity: 卖出数量
        fee_rate: 手续费率
    
    Returns:
        (更新后的现金, 更新后的持仓字典, 交易结果)
    """
    if code not in positions:
        return cash, positions, TradeResult(
            success=False,
            code=code,
            action='SELL',
            price=price,
            quantity=quantity,
            reason='无持仓',
        )
    
    pos = positions[code]
    if pos.shares < quantity:
        return cash, positions, TradeResult(
            success=False,
            code=code,
            action='SELL',
            price=price,
            quantity=quantity,
            reason=f'持仓不足(持有{pos.shares}股)',
        )
    
    trade = simulate_trade('SELL', price, quantity, fee_rate)
    new_cash = cash + trade['net_proceeds']
    
    new_shares = pos.shares - quantity
    if new_shares == 0:
        del positions[code]
    else:
        positions[code] = Position(
            code=code,
            shares=new_shares,
            entry_price=pos.entry_price,
            entry_date=pos.entry_date,
            hold_days=pos.hold_days,
        )
    
    return new_cash, positions, TradeResult(
        success=True,
        code=code,
        action='SELL',
        price=price,
        quantity=quantity,
        fee=trade['fee'],
        net_proceeds=trade['net_proceeds'],
        position=positions.get(code),
    )
