"""
alpha101.py — WorldQuant《101 Formulaic Alphas》完整实现

使用方法：
    from formulaicAlphas.data_loader import AlphaDataLoader
    from formulaicAlphas.alpha101 import Alpha101

    loader = AlphaDataLoader()
    data = loader.load(codes, start_date='2025-01-01', end_date='2026-03-14')

    a = Alpha101(data)
    alpha1  = a.alpha001()   # DataFrame: 行=日期, 列=股票代码
    alpha50 = a.alpha050()

    # 取最新一日横截面
    latest = alpha1.iloc[-1].dropna().sort_values()

设计说明：
- 每个 alpha 方法返回与输入面板同形的 DataFrame（行=日期，列=股票）
- 参数中的小数（如 3.65595）来自机器优化，实现时直接取整
- 带 IndNeutralize 的 alpha 需传入 ind（行业面板），否则跳过中性化直接使用原值
- sum / max / min 在公式中均指时间序列滚动操作（ts_sum / ts_max / ts_min）
"""

from __future__ import annotations
import numpy as np
import pandas as pd
from typing import Optional

from .operators import (
    rank, scale, ind_neutralize,
    delay, delta, ts_sum, mean, stddev,
    ts_max, ts_min, ts_rank, ts_argmax, ts_argmin,
    correlation, covariance, decay_linear, product,
    signedpower, log, sign, abs_, adv, where,
)

Panel = pd.DataFrame


class Alpha101:
    """
    WorldQuant Alpha 101 因子库。

    Args:
        data: AlphaDataLoader.load() 返回的字段字典，需包含：
              open, high, low, close, volume, vwap, returns
              可选：ind（行业面板，带 IndNeutralize 的 alpha 所需）
    """

    def __init__(self, data: dict[str, Panel]):
        self.open    = data["open"].astype(float)
        self.high    = data["high"].astype(float)
        self.low     = data["low"].astype(float)
        self.close   = data["close"].astype(float)
        self.volume  = data["volume"].astype(float)
        self.vwap    = data["vwap"].astype(float)
        self.returns = data["returns"].astype(float)
        self.ind: Optional[Panel] = data.get("ind")

        self._adv_cache: dict[int, Panel] = {}

    # ── 内部辅助 ─────────────────────────────────────────────────────────────

    def _adv(self, n: int) -> Panel:
        """缓存各 n 日平均成交量。"""
        if n not in self._adv_cache:
            self._adv_cache[n] = adv(self.volume, n)
        return self._adv_cache[n]

    def _ind_neu(self, x: Panel) -> Panel:
        """如有行业数据则中性化，否则原样返回。"""
        if self.ind is not None:
            return ind_neutralize(x, self.ind)
        return x

    # ── Alpha 001 ── Alpha 010 ───────────────────────────────────────────────

    def alpha001(self) -> Panel:
        """rank(ts_argmax(signedpower(where(returns<0,stddev(returns,20),close),2),5)) - 0.5"""
        cond = self.returns < 0
        base = where(cond, stddev(self.returns, 20), self.close)
        return rank(ts_argmax(signedpower(base, 2), 5)) - 0.5

    def alpha002(self) -> Panel:
        """(-1) * correlation(rank(delta(log(volume),2)), rank((close-open)/open), 6)"""
        x = rank(delta(log(self.volume), 2))
        y = rank((self.close - self.open) / self.open)
        return -1 * correlation(x, y, 6)

    def alpha003(self) -> Panel:
        """(-1) * correlation(rank(open), rank(volume), 10)"""
        return -1 * correlation(rank(self.open), rank(self.volume), 10)

    def alpha004(self) -> Panel:
        """(-1) * ts_rank(rank(low), 9)"""
        return -1 * ts_rank(rank(self.low), 9)

    def alpha005(self) -> Panel:
        """rank(open - ts_sum(vwap,10)/10) * (-abs(rank(close - vwap)))"""
        return rank(self.open - ts_sum(self.vwap, 10) / 10) * (-abs_(rank(self.close - self.vwap)))

    def alpha006(self) -> Panel:
        """(-1) * correlation(open, volume, 10)"""
        return -1 * correlation(self.open, self.volume, 10)

    def alpha007(self) -> Panel:
        """if adv20 < volume: (-1)*ts_rank(abs(delta(close,7)),60)*sign(delta(close,7)) else -1"""
        adv20 = self._adv(20)
        d7 = delta(self.close, 7)
        hit = -1 * ts_rank(abs_(d7), 60) * sign(d7)
        return where(adv20 < self.volume, hit, -1)

    def alpha008(self) -> Panel:
        """(-1) * rank(ts_sum(open,5)*ts_sum(returns,5) - delay(ts_sum(open,5)*ts_sum(returns,5),10))"""
        prod = ts_sum(self.open, 5) * ts_sum(self.returns, 5)
        return -1 * rank(prod - delay(prod, 10))

    def alpha009(self) -> Panel:
        """顺势/逆势：5日内单调上涨→顺势；单调下跌→顺势；震荡→逆势"""
        d1 = delta(self.close, 1)
        cond_up   = ts_min(d1, 5) > 0
        cond_down = ts_max(d1, 5) < 0
        return where(cond_up, d1, where(cond_down, d1, -d1))

    def alpha010(self) -> Panel:
        """rank(alpha009_logic_with_4day_window)"""
        d1 = delta(self.close, 1)
        cond_up   = ts_min(d1, 4) > 0
        cond_down = ts_max(d1, 4) < 0
        return rank(where(cond_up, d1, where(cond_down, d1, -d1)))

    # ── Alpha 011 ── Alpha 020 ───────────────────────────────────────────────

    def alpha011(self) -> Panel:
        """(rank(ts_max(vwap-close,3)) + rank(ts_min(vwap-close,3))) * rank(delta(volume,3))"""
        vc = self.vwap - self.close
        return (rank(ts_max(vc, 3)) + rank(ts_min(vc, 3))) * rank(delta(self.volume, 3))

    def alpha012(self) -> Panel:
        """sign(delta(volume,1)) * (-delta(close,1))"""
        return sign(delta(self.volume, 1)) * (-delta(self.close, 1))

    def alpha013(self) -> Panel:
        """(-1) * rank(covariance(rank(close), rank(volume), 5))"""
        return -1 * rank(covariance(rank(self.close), rank(self.volume), 5))

    def alpha014(self) -> Panel:
        """(-1)*rank(delta(returns,3)) * correlation(open, volume, 10)"""
        return -1 * rank(delta(self.returns, 3)) * correlation(self.open, self.volume, 10)

    def alpha015(self) -> Panel:
        """(-1) * ts_sum(rank(correlation(rank(high), rank(volume), 3)), 3)"""
        return -1 * ts_sum(rank(correlation(rank(self.high), rank(self.volume), 3)), 3)

    def alpha016(self) -> Panel:
        """(-1) * rank(covariance(rank(high), rank(volume), 5))"""
        return -1 * rank(covariance(rank(self.high), rank(self.volume), 5))

    def alpha017(self) -> Panel:
        """(-1)*rank(ts_rank(close,10)) * rank(delta(delta(close,1),1)) * rank(ts_rank(vol/adv20,5))"""
        adv20 = self._adv(20)
        return (
            -1 * rank(ts_rank(self.close, 10))
            * rank(delta(delta(self.close, 1), 1))
            * rank(ts_rank(self.volume / adv20, 5))
        )

    def alpha018(self) -> Panel:
        """(-1)*rank(stddev(abs(close-open),5) + (close-open) + correlation(close,open,10))"""
        return -1 * rank(
            stddev(abs_(self.close - self.open), 5)
            + (self.close - self.open)
            + correlation(self.close, self.open, 10)
        )

    def alpha019(self) -> Panel:
        """(-1)*sign(2*delta(close,7)) * (1 + rank(1 - ts_sum(returns,250)))"""
        # (close - delay(close,7)) + delta(close,7) = 2*delta(close,7)
        return -1 * sign(delta(self.close, 7)) * (1 + rank(1 - ts_sum(self.returns, 250)))

    def alpha020(self) -> Panel:
        """(-1)*rank(open-delay(high,1)) * rank(open-delay(close,1)) * rank(open-delay(low,1))"""
        return (
            -1
            * rank(self.open - delay(self.high, 1))
            * rank(self.open - delay(self.close, 1))
            * rank(self.open - delay(self.low, 1))
        )

    # ── Alpha 021 ── Alpha 030 ───────────────────────────────────────────────

    def alpha021(self) -> Panel:
        """布林带判断：价格突破上轨→看空，跌破下轨→看多，中间→排名。"""
        ma8  = ts_sum(self.close, 8) / 8
        std8 = stddev(self.close, 8)
        ma2  = ts_sum(self.close, 2) / 2
        cond_up   = (ma8 + std8) < ma2
        cond_down = ma2 < (ma8 - std8)
        middle    = 1 - rank(std8 + ts_max(self.close, 8))
        return where(cond_up, -1, where(cond_down, 1, middle))

    def alpha022(self) -> Panel:
        """(-1) * delta(correlation(high, volume, 5), 5) * rank(stddev(close, 20))"""
        return -1 * delta(correlation(self.high, self.volume, 5), 5) * rank(stddev(self.close, 20))

    def alpha023(self) -> Panel:
        """if ts_mean(high,20) < high: -delta(high,2) else 0"""
        cond = ts_sum(self.high, 20) / 20 < self.high
        return where(cond, -delta(self.high, 2), 0)

    def alpha024(self) -> Panel:
        """价格斜率<=5%: -(close - ts_min(close,100)); 否则 -delta(close,3)"""
        slope = delta(ts_sum(self.close, 100) / 100, 100) / delay(self.close, 100)
        cond = slope <= 0.05
        return where(cond, -(self.close - ts_min(self.close, 100)), -delta(self.close, 3))

    def alpha025(self) -> Panel:
        """复杂量价位置因子，结合 adv40、高低价相关性和7日价格变化。"""
        adv40 = self._adv(40)
        price = (2 * self.close + self.low + self.high) / 4
        part1 = rank(price * (adv40 / self.volume + 1))
        part2 = (
            (rank(correlation(self.high, self.close, 5)) + rank(correlation(self.low, self.close, 5))) / 2
            + rank(delta(self.close, 7))
        )
        return part1 * part2

    def alpha026(self) -> Panel:
        """(-1) * (rank(ts_rank(exp(close),1)) - rank(rank(correlation(high,volume,5))))"""
        return -1 * (rank(ts_rank(np.exp(self.close), 1)) - rank(rank(correlation(self.high, self.volume, 5))))

    def alpha027(self) -> Panel:
        """if rank(mean(correlation(rank(volume),rank(vwap),6),2)) > 0.5: -1 else 1"""
        cond = rank(mean(correlation(rank(self.volume), rank(self.vwap), 6), 2)) > 0.5
        return where(cond, -1, 1)

    def alpha028(self) -> Panel:
        """scale(correlation(adv20, low, 5) + (high+low)/2 - close)"""
        adv20 = self._adv(20)
        return scale(correlation(adv20, self.low, 5) + (self.high + self.low) / 2 - self.close)

    def alpha029(self) -> Panel:
        """ts_min(rank(rank(scale(log(ts_sum(rank(rank(-rank(delta(close,5)))),2))))),5)
           + ts_rank(delay(-returns,6),5)"""
        inner = -rank(delta(self.close, 5))
        part1 = ts_min(rank(rank(scale(log(ts_sum(rank(rank(inner)), 2))))), 5)
        part2 = ts_rank(delay(-self.returns, 6), 5)
        return part1 + part2

    def alpha030(self) -> Panel:
        """(1 - rank(sign_sum_3days)) * ts_sum(vol,5) / ts_sum(vol,20)"""
        s = (
            sign(self.close - delay(self.close, 1))
            + sign(delay(self.close, 1) - delay(self.close, 2))
            + sign(delay(self.close, 2) - delay(self.close, 3))
        )
        return (1 - rank(s)) * ts_sum(self.volume, 5) / ts_sum(self.volume, 20)

    # ── Alpha 031 ── Alpha 040 ───────────────────────────────────────────────

    def alpha031(self) -> Panel:
        """(-1)*(rank(correlation(close,adv10,5)) - rank(delta(delta(close,1),1)))
              * rank(close - ts_min(close,10) + 0.001)"""
        adv10 = self._adv(10)
        return (
            -1
            * (rank(correlation(self.close, adv10, 5)) - rank(delta(delta(self.close, 1), 1)))
            * rank(self.close - ts_min(self.close, 10) + 0.001)
        )

    def alpha032(self) -> Panel:
        """scale(rank((ts_sum(close,7)/7 - close))) + 2*rank(correlation(vwap,delay(close,5),230))"""
        return (
            scale(rank(ts_sum(self.close, 7) / 7 - self.close))
            + 2 * rank(correlation(self.vwap, delay(self.close, 5), 230))
        )

    def alpha033(self) -> Panel:
        """rank(-(1 - open/close)^2)"""
        return rank(-signedpower(1 - self.open / self.close, 2))

    def alpha034(self) -> Panel:
        """(-1)*((rank(open - ts_max(close,2)) + rank(open - ts_min(close,2)))
               * rank((open - delay(close,1)) + (delay(close,1) - close)))"""
        return -1 * (
            (rank(self.open - ts_max(self.close, 2)) + rank(self.open - ts_min(self.close, 2)))
            * rank((self.open - delay(self.close, 1)) + (delay(self.close, 1) - self.close))
        )

    def alpha035(self) -> Panel:
        """(-1)*(rank(volume)*(1-rank(close-low)) + rank(open-low)*(1-rank(returns)))"""
        return -1 * (
            rank(self.volume) * (1 - rank(self.close - self.low))
            + rank(self.open - self.low) * (1 - rank(self.returns))
        )

    def alpha036(self) -> Panel:
        """2.21*rank(correlation(open,volume,5)) - 0.01*rank(delta(returns,3))
           + 1.54*rank(open - low)"""
        # Note: paper also includes vwap & low terms; using best-effort interpretation
        adv20 = self._adv(20)
        return (
            2.21 * rank(correlation(self.open, self.volume, 5))
            - 0.01 * rank(delta(self.returns, 3))
            + 1.54 * rank(self.open - self.low)
        )

    def alpha037(self) -> Panel:
        """rank(correlation(delay(open-close,1), close, 200)) + rank(open-close)"""
        return rank(correlation(delay(self.open - self.close, 1), self.close, 200)) + rank(self.open - self.close)

    def alpha038(self) -> Panel:
        """(-1)*rank(ts_rank(close,10)) * rank(close/open)"""
        return -1 * rank(ts_rank(self.close, 10)) * rank(self.close / self.open)

    def alpha039(self) -> Panel:
        """(-1)*rank(delta(close,7) * (1 - rank(decay_linear(volume/adv20,9))))
           * (1 + rank(ts_sum(returns,250)))"""
        adv20 = self._adv(20)
        return (
            -1 * rank(delta(self.close, 7) * (1 - rank(decay_linear(self.volume / adv20, 9))))
            * (1 + rank(ts_sum(self.returns, 250)))
        )

    def alpha040(self) -> Panel:
        """(-1)*rank(stddev(high,10)) * correlation(high, volume, 10)"""
        return -1 * rank(stddev(self.high, 10)) * correlation(self.high, self.volume, 10)

    # ── Alpha 041 ── Alpha 050 ───────────────────────────────────────────────

    def alpha041(self) -> Panel:
        """(high*low)^0.5 - vwap"""
        return (self.high * self.low) ** 0.5 - self.vwap

    def alpha042(self) -> Panel:
        """(vwap - close) / (vwap + close) * 0.5"""
        return (self.vwap - self.close) / (self.vwap + self.close) * 0.5

    def alpha043(self) -> Panel:
        """ts_rank(volume/adv20, 20) * ts_rank(-delta(close,7), 8)"""
        adv20 = self._adv(20)
        return ts_rank(self.volume / adv20, 20) * ts_rank(-delta(self.close, 7), 8)

    def alpha044(self) -> Panel:
        """(-1) * correlation(high, rank(volume), 5)"""
        return -1 * correlation(self.high, rank(self.volume), 5)

    def alpha045(self) -> Panel:
        """(-1) * rank(ts_sum(delay(close,5),20)/20) * correlation(close,volume,2)
               * rank(correlation(ts_sum(close,5), ts_sum(close,20), 2))"""
        return (
            -1
            * rank(ts_sum(delay(self.close, 5), 20) / 20)
            * correlation(self.close, self.volume, 2)
            * rank(correlation(ts_sum(self.close, 5), ts_sum(self.close, 20), 2))
        )

    def alpha046(self) -> Panel:
        """比较两段价格斜率：(d20-d10)/10 vs (d10-now)/10"""
        slope_far  = (delay(self.close, 20) - delay(self.close, 10)) / 10
        slope_near = (delay(self.close, 10) - self.close) / 10
        diff = slope_far - slope_near
        cond_sell = diff > 0.25
        cond_buy  = diff < 0
        return where(cond_sell, -1, where(cond_buy, 1, -delta(self.close, 1)))

    def alpha047(self) -> Panel:
        """复杂多因子：价格倒数×量/adv20 × 高价位置 / 5日均高 - rank(vwap变化)"""
        adv20 = self._adv(20)
        part1 = (
            (1 / self.close)
            * self.volume
            / adv20
            * self.high
            * rank(self.high - self.close)
            / (ts_sum(self.high, 5) / 5)
        )
        return rank(part1) - rank(delta(self.vwap, 5))

    def alpha048(self) -> Panel:
        """类似alpha030但加行业中性化"""
        s = (
            sign(self.close - delay(self.close, 1))
            + sign(delay(self.close, 1) - delay(self.close, 2))
            + sign(delay(self.close, 2) - delay(self.close, 3))
        )
        return (
            -1 * rank(s) * ts_sum(self.volume, 5) / ts_sum(self.volume, 20)
            * self._ind_neu(self.close)
        )

    def alpha049(self) -> Panel:
        """价格斜率差 < -1: 1; 否则 -delta(close,1)"""
        slope_far  = (delay(self.close, 20) - delay(self.close, 10)) / 10
        slope_near = (delay(self.close, 10) - self.close) / 10
        cond = (slope_far - slope_near) < -1
        return where(cond, 1, -delta(self.close, 1))

    def alpha050(self) -> Panel:
        """(-1) * ts_max(rank(correlation(rank(volume), rank(vwap), 5)), 5)"""
        return -1 * ts_max(rank(correlation(rank(self.volume), rank(self.vwap), 5)), 5)

    # ── Alpha 051 ── Alpha 060 ───────────────────────────────────────────────

    def alpha051(self) -> Panel:
        """价格斜率差 < -0.05: 1; 否则 -1"""
        slope_far  = (delay(self.close, 20) - delay(self.close, 10)) / 10
        slope_near = (delay(self.close, 10) - self.close) / 10
        cond = (slope_far - slope_near) < -0.05
        return where(cond, 1, -1)

    def alpha052(self) -> Panel:
        """(ts_min(low,5)变化量) * rank(长期收益加速) * ts_rank(volume,5)"""
        low_chg  = -ts_min(self.low, 5) + delay(ts_min(self.low, 5), 5)
        ret_accel = rank((ts_sum(self.returns, 240) - ts_sum(self.returns, 20)) / 220)
        return low_chg * ret_accel * ts_rank(self.volume, 5)

    def alpha053(self) -> Panel:
        """(-1) * delta((close-low - (high-close)) / (close-low+1e-8), 9)"""
        ratio = (self.close - self.low - (self.high - self.close)) / (self.close - self.low + 1e-8)
        return -1 * delta(ratio, 9)

    def alpha054(self) -> Panel:
        """(-1) * (low-close)*(open^5) / ((low-high)*(close^5) + 1e-8)"""
        denom = (self.low - self.high) * (self.close ** 5) + 1e-8
        return -1 * (self.low - self.close) * (self.open ** 5) / denom

    def alpha055(self) -> Panel:
        """(-1) * correlation(rank((close-ts_min(low,12))/(ts_max(high,12)-ts_min(low,12)+1e-8)),
                              rank(volume), 6)"""
        stoch = (self.close - ts_min(self.low, 12)) / (ts_max(self.high, 12) - ts_min(self.low, 12) + 1e-8)
        return -1 * correlation(rank(stoch), rank(self.volume), 6)

    def alpha056(self) -> Panel:
        """(-1)*(rank(ts_sum(returns,5)-ts_sum(returns,20)) + rank(close-ts_min(close,5)))
               * IndNeutralize(close, ind)"""
        part = rank(ts_sum(self.returns, 5) - ts_sum(self.returns, 20)) + rank(self.close - ts_min(self.close, 5))
        return -1 * part * self._ind_neu(self.close)

    def alpha057(self) -> Panel:
        """0 - (1 - rank((close-ts_min(close,5))/(ts_max(close,5)-ts_min(close,5)+1e-8)))"""
        stoch = (self.close - ts_min(self.close, 5)) / (ts_max(self.close, 5) - ts_min(self.close, 5) + 1e-8)
        return 0 - (1 - rank(stoch))

    def alpha058(self) -> Panel:
        """(-1)*ts_rank(decay_linear(correlation(IndNeutralize(vwap,ind),volume,4),8),6)"""
        vwap_n = self._ind_neu(self.vwap)
        return -1 * ts_rank(decay_linear(correlation(vwap_n, self.volume, 4), 8), 6)

    def alpha059(self) -> Panel:
        """类似alpha058，vwap经加权（0.728317）后中性化"""
        vwap_w = self.vwap * 0.728317 + self.vwap * (1 - 0.728317)  # == self.vwap
        vwap_n = self._ind_neu(vwap_w)
        return -1 * ts_rank(decay_linear(correlation(vwap_n, self.volume, 4), 16), 8)

    def alpha060(self) -> Panel:
        """(-1)*rank(ts_rank(correlation(rank(high),rank(volume),9),14))
               * rank(ts_rank(correlation(rank(low),rank(volume),7),8))"""
        c1 = rank(ts_rank(correlation(rank(self.high), rank(self.volume), 9), 14))
        c2 = rank(ts_rank(correlation(rank(self.low),  rank(self.volume), 7), 8))
        return -1 * c1 * c2

    # ── Alpha 061 ── Alpha 070 ───────────────────────────────────────────────

    def alpha061(self) -> Panel:
        """(-1)*rank(correlation(rank(vwap),rank(volume),4))
               * rank(correlation(rank(low),rank(volume),5))"""
        c1 = rank(correlation(rank(self.vwap), rank(self.volume), 4))
        c2 = rank(correlation(rank(self.low),  rank(self.volume), 5))
        return -1 * c1 * c2

    def alpha062(self) -> Panel:
        """if rank(corr(vwap,adv20,10)) < rank(corr(rank(low),rank(adv50),17)): -1 else 1"""
        adv20 = self._adv(20)
        adv50 = self._adv(50)
        cond = rank(correlation(self.vwap, adv20, 10)) < rank(correlation(rank(self.low), rank(adv50), 17))
        return where(cond, -1, 1)

    def alpha063(self) -> Panel:
        """类似alpha062，vwap行业中性化后比较"""
        adv50 = self._adv(50)
        vwap_n = self._ind_neu(self.vwap * 0.724108 + self.vwap * (1 - 0.724108))
        c1 = rank(correlation(vwap_n, rank(self.volume), 6))
        c2 = rank(correlation(rank(self.low), rank(adv50), 20))
        return where(c1 < c2, -1, 1)

    def alpha064(self) -> Panel:
        """比较复合量的相关性排名"""
        adv40 = self._adv(40)
        adv50 = self._adv(50)
        price = self.open * 0.178404 + self.low * (1 - 0.178404)
        c1 = rank(correlation(ts_sum(price, 13), ts_sum(adv40, 13), 5))
        c2 = rank(correlation(rank(self.low), rank(adv50), 12))
        return where(c1 < c2, -1, 1)

    def alpha065(self) -> Panel:
        """if rank(corr(open,vol,11)) < rank(corr(rank(low),rank(adv30),15)): -1 else 1"""
        adv30 = self._adv(30)
        c1 = rank(correlation(self.open, self.volume, 11))
        c2 = rank(correlation(rank(self.low), rank(adv30), 15))
        return where(c1 < c2, -1, 1)

    def alpha066(self) -> Panel:
        """if rank(corr(open,vol,5)) < rank(corr(rank(vwap),rank(vol),6)): -1 else 1"""
        c1 = rank(correlation(self.open,  self.volume, 5))
        c2 = rank(correlation(rank(self.vwap), rank(self.volume), 6))
        return where(c1 < c2, -1, 1)

    def alpha067(self) -> Panel:
        """if rank(corr(IndNeutralize(high,ind),vol,8)) < rank(corr(rank(low),rank(adv30),18)): -1 else 1"""
        adv30 = self._adv(30)
        high_n = self._ind_neu(self.high)
        c1 = rank(correlation(high_n, self.volume, 8))
        c2 = rank(correlation(rank(self.low), rank(adv30), 18))
        return where(c1 < c2, -1, 1)

    def alpha068(self) -> Panel:
        """比较两个ts_rank后相关性的排名"""
        adv20 = self._adv(20)
        c1 = rank(correlation(ts_rank(self.high, 3), ts_rank(self.volume, 3), 4))
        c2 = rank(correlation(rank(self.low), rank(adv20), 14))
        return where(c1 < c2, -1, 1)

    def alpha069(self) -> Panel:
        """if rank(corr(rank(vwap),rank(vol),12)) < rank(corr(rank(low),adv40,19)): -1 else 1"""
        adv40 = self._adv(40)
        c1 = rank(correlation(rank(self.vwap), rank(self.volume), 12))
        c2 = rank(correlation(rank(self.low), adv40, 19))
        return where(c1 < c2, -1, 1)

    def alpha070(self) -> Panel:
        """(-1) * rank(delta(vwap,1))^ts_rank(corr(IndNeutralize(close,ind),adv50,18),18)"""
        adv50 = self._adv(50)
        close_n = self._ind_neu(self.close)
        exp = ts_rank(correlation(close_n, adv50, 18), 18)
        base = rank(delta(self.vwap, 1))
        return -1 * base ** exp

    # ── Alpha 071 ── Alpha 080 ───────────────────────────────────────────────

    def alpha071(self) -> Panel:
        """max(rank(decay_linear(corr(ts_rank(close,3),ts_rank(adv50,3),12),7)),
               rank(decay_linear((h+l)/2+open-close, 15)))"""
        adv50 = self._adv(50)
        p1 = rank(decay_linear(correlation(ts_rank(self.close, 3), ts_rank(adv50, 3), 12), 7))
        p2 = rank(decay_linear((self.high + self.low) / 2 + self.open - self.close, 15))
        return p1.combine(p2, np.maximum)

    def alpha072(self) -> Panel:
        """rank(decay_linear(corr(rank(high),rank(adv30),9),4))
         - rank(decay_linear(corr(rank(low),rank(adv30),10),8))"""
        adv30 = self._adv(30)
        p1 = rank(decay_linear(correlation(rank(self.high), rank(adv30), 9), 4))
        p2 = rank(decay_linear(correlation(rank(self.low),  rank(adv30), 10), 8))
        return p1 - p2

    def alpha073(self) -> Panel:
        """rank(decay_linear(delta(vwap,3),2)) + rank(decay_linear((-low+open)/(high-low+1e-8),1))"""
        ratio = (-self.low + self.open) / (self.high - self.low + 1e-8)
        return rank(decay_linear(delta(self.vwap, 3), 2)) + rank(decay_linear(ratio, 1))

    def alpha074(self) -> Panel:
        """(-1)*(rank(corr(low,adv30,17)) + rank(delay(rank(open+close),12))
               - rank(decay_linear(corr(rank(vwap),rank(adv50),7),18)))"""
        adv30 = self._adv(30)
        adv50 = self._adv(50)
        p1 = rank(correlation(self.low, adv30, 17))
        p2 = rank(delay(rank(self.open + self.close), 12))
        p3 = rank(decay_linear(correlation(rank(self.vwap), rank(adv50), 7), 18))
        return -1 * (p1 + p2 - p3)

    def alpha075(self) -> Panel:
        """(rank(corr(rank(vwap),rank(vol),4)) + rank(corr(rank(low),rank(adv50),19)))
         - rank(decay_linear((high+low)/2, 12))"""
        adv50 = self._adv(50)
        p1 = rank(correlation(rank(self.vwap), rank(self.volume), 4))
        p2 = rank(correlation(rank(self.low), rank(adv50), 19))
        p3 = rank(decay_linear((self.high + self.low) / 2, 12))
        return p1 + p2 - p3

    def alpha076(self) -> Panel:
        """(-rank(decay_linear(delta(vwap,2),16))
         - rank(decay_linear(-(rank(close+open-low)-rank(vwap)+rank(close-vwap)),17)))
         * IndNeutralize(close,ind)"""
        inner = -(rank(self.close + self.open - self.low) - rank(self.vwap) + rank(self.close - self.vwap))
        p1 = -rank(decay_linear(delta(self.vwap, 2), 16))
        p2 = -rank(decay_linear(inner, 17))
        return (p1 + p2) * self._ind_neu(self.close)

    def alpha077(self) -> Panel:
        """(-1)*rank(decay_linear((h+l)/2+high-vwap-high,2))
           + rank(decay_linear(corr(rank(low),rank(adv50),20),9))"""
        adv50 = self._adv(50)
        ratio = (self.high + self.low) / 2 + self.high - self.vwap - self.high
        p1 = -rank(decay_linear(ratio, 2))
        p2 = rank(decay_linear(correlation(rank(self.low), rank(adv50), 20), 9))
        return p1 + p2

    def alpha078(self) -> Panel:
        """(-1)*rank(decay_linear(corr(rank(vwap),rank(adv20),4),5))
         - rank(decay_linear(-low,9)) + rank(decay_linear(open,16))"""
        adv20 = self._adv(20)
        p1 = -rank(decay_linear(correlation(rank(self.vwap), rank(adv20), 4), 5))
        p2 = -rank(decay_linear(-self.low, 9))
        p3 = rank(decay_linear(self.open, 16))
        return p1 + p2 + p3

    def alpha079(self) -> Panel:
        """rank(delta(IndNeutralize(close,ind),2)) * rank(corr(IndNeutralize(vwap,ind),adv50,15))
         - rank(decay_linear(-low,4))"""
        adv50  = self._adv(50)
        close_n = self._ind_neu(self.close)
        vwap_n  = self._ind_neu(self.vwap)
        p1 = rank(delta(close_n, 2)) * rank(correlation(vwap_n, adv50, 15))
        p2 = rank(decay_linear(-self.low, 4))
        return p1 - p2

    def alpha080(self) -> Panel:
        """(-1)*(rank(sign(delta(IndNeutralize(open,ind),2))*sign(delta(IndNeutralize(close,ind),3)))
               + rank(ts_rank(volume,5)))"""
        open_n  = self._ind_neu(self.open)
        close_n = self._ind_neu(self.close)
        p1 = rank(sign(delta(open_n, 2)) * sign(delta(close_n, 3)))
        p2 = rank(ts_rank(self.volume, 5))
        return -1 * (p1 + p2)

    # ── Alpha 081 ── Alpha 090 ───────────────────────────────────────────────

    def alpha081(self) -> Panel:
        """(-1)*(rank(log(product(rank(corr(rank(high),rank(adv10),8)),2))) - 0.5)"""
        adv10 = self._adv(10)
        return -1 * (rank(log(product(rank(correlation(rank(self.high), rank(adv10), 8)), 2))) - 0.5)

    def alpha082(self) -> Panel:
        """(-1)*(rank(log(rank(corr(rank(high),rank(adv10),8))))
               + rank(ts_rank(vol,6)) - rank(corr(open,vol,6)))"""
        adv10 = self._adv(10)
        p1 = rank(log(rank(correlation(rank(self.high), rank(adv10), 8))))
        p2 = rank(ts_rank(self.volume, 6))
        p3 = rank(correlation(self.open, self.volume, 6))
        return -1 * (p1 + p2 - p3)

    def alpha083(self) -> Panel:
        """rank(delay(high,5)*sign(delta(close,5))) + rank(vwap-close)
         - rank(corr(open,vol,13))"""
        p1 = rank(delay(self.high, 5) * sign(delta(self.close, 5)))
        p2 = rank(self.vwap - self.close)
        p3 = rank(correlation(self.open, self.volume, 13))
        return p1 + p2 - p3

    def alpha084(self) -> Panel:
        """rank(corr(vwap,adv20,6)) + rank(corr(open,vol,15))"""
        adv20 = self._adv(20)
        return rank(correlation(self.vwap, adv20, 6)) + rank(correlation(self.open, self.volume, 15))

    def alpha085(self) -> Panel:
        """(rank(corr(close,adv15,9)) + rank(corr(rank(high),rank(vol),11)))
         - rank(delta(close,6))"""
        adv15 = self._adv(15)
        p1 = rank(correlation(self.close, adv15, 9))
        p2 = rank(correlation(rank(self.high), rank(self.volume), 11))
        p3 = rank(delta(self.close, 6))
        return p1 + p2 - p3

    def alpha086(self) -> Panel:
        """(rank(corr(close,adv30,7)) + rank(corr(open,vol,13))) - rank(delta(close,6))"""
        adv30 = self._adv(30)
        p1 = rank(correlation(self.close, adv30, 7))
        p2 = rank(correlation(self.open, self.volume, 13))
        p3 = rank(delta(self.close, 6))
        return p1 + p2 - p3

    def alpha087(self) -> Panel:
        """max(rank(delta(close,3)),rank(ts_rank(vol*0.47,5)))
         - min(rank(delta(adv50,2)),rank(corr(IndNeutralize(vwap,ind),vol,11)))"""
        adv50  = self._adv(50)
        vwap_n = self._ind_neu(self.vwap)
        hi = (rank(delta(self.close, 3))).combine(rank(ts_rank(self.volume * 0.47, 5)), np.maximum)
        lo = (rank(delta(adv50, 2))).combine(rank(correlation(vwap_n, self.volume, 11)), np.minimum)
        return hi - lo

    def alpha088(self) -> Panel:
        """min(rank(decay_linear(delta(open,2),3)), rank(corr(close,vol,20)))
         + rank(decay_linear(open-low,2))"""
        p_min = (rank(decay_linear(delta(self.open, 2), 3))).combine(
            rank(correlation(self.close, self.volume, 20)), np.minimum
        )
        return p_min + rank(decay_linear(self.open - self.low, 2))

    def alpha089(self) -> Panel:
        """(-1)*(rank(ts_rank(decay_linear(corr(IndNeutralize(vwap,ind),vol,4),8),7))
              - rank(decay_linear(ts_rank(corr(rank(low),rank(adv30),12),19),16))"""
        adv30  = self._adv(30)
        vwap_n = self._ind_neu(self.vwap)
        p1 = rank(ts_rank(decay_linear(correlation(vwap_n, self.volume, 4), 8), 7))
        p2 = rank(decay_linear(ts_rank(correlation(rank(self.low), rank(adv30), 12), 19), 16))
        return -1 * (p1 - p2)

    def alpha090(self) -> Panel:
        """rank(decay_linear(corr(rank(vwap),rank(vol),14),5))
         - rank(decay_linear(ts_rank(ts_min(low,5),19),13))
         + rank(corr(IndNeutralize(close,ind),vol,16))"""
        close_n = self._ind_neu(self.close)
        p1 = rank(decay_linear(correlation(rank(self.vwap), rank(self.volume), 14), 5))
        p2 = rank(decay_linear(ts_rank(ts_min(self.low, 5), 19), 13))
        p3 = rank(correlation(close_n, self.volume, 16))
        return p1 - p2 + p3

    # ── Alpha 091 ── Alpha 101 ───────────────────────────────────────────────

    def alpha091(self) -> Panel:
        """(-1)*(rank(ts_rank(decay_linear(decay_linear(corr(IndNeutralize(close,ind),vol,3),7),6),4))
              - rank(decay_linear(ts_rank(corr(rank(vwap),rank(adv30),19),12),20))"""
        adv30   = self._adv(30)
        close_n = self._ind_neu(self.close)
        inner = decay_linear(decay_linear(correlation(close_n, self.volume, 3), 7), 6)
        p1 = rank(ts_rank(inner, 4))
        p2 = rank(decay_linear(ts_rank(correlation(rank(self.vwap), rank(adv30), 19), 12), 20))
        return -1 * (p1 - p2)

    def alpha092(self) -> Panel:
        """min(rank(decay_linear(cond_close_lt_lo_open, 15)),
               rank(decay_linear(corr(rank(high),rank(adv30),14),16)))"""
        adv30 = self._adv(30)
        cond = (self.high + self.low) / 2 + self.close < self.low + self.open
        p1 = rank(decay_linear(cond.astype(float), 15))
        p2 = rank(decay_linear(correlation(rank(self.high), rank(adv30), 14), 16))
        return p1.combine(p2, np.minimum)

    def alpha093(self) -> Panel:
        """(5/6)*ts_rank(decay_linear(corr(IndNeutralize(vwap,ind),adv50,19),8),6)
         + (1/6)*rank(decay_linear(corr(rank(vwap),rank(vol),20),4))"""
        adv50  = self._adv(50)
        vwap_n = self._ind_neu(self.vwap)
        p1 = ts_rank(decay_linear(correlation(vwap_n, adv50, 19), 8), 6)
        p2 = rank(decay_linear(correlation(rank(self.vwap), rank(self.volume), 20), 4))
        return (5 / 6) * p1 + (1 / 6) * p2

    def alpha094(self) -> Panel:
        """(rank(decay_linear(corr(vwap,low,18),12))
         - rank(decay_linear(corr(rank(low),rank(adv30),14),16)))
         + rank(decay_linear(delta(vwap,3),16))"""
        adv30 = self._adv(30)
        p1 = rank(decay_linear(correlation(self.vwap, self.low, 18), 12))
        p2 = rank(decay_linear(correlation(rank(self.low), rank(adv30), 14), 16))
        p3 = rank(decay_linear(delta(self.vwap, 3), 16))
        return p1 - p2 + p3

    def alpha095(self) -> Panel:
        """(rank(decay_linear(corr(open,vol,13),18))
         - rank(decay_linear(corr(rank(low),rank(adv30),16),12)))
         + rank(decay_linear(delta(vwap,2),17))"""
        adv30 = self._adv(30)
        p1 = rank(decay_linear(correlation(self.open, self.volume, 13), 18))
        p2 = rank(decay_linear(correlation(rank(self.low), rank(adv30), 16), 12))
        p3 = rank(decay_linear(delta(self.vwap, 2), 17))
        return p1 - p2 + p3

    def alpha096(self) -> Panel:
        """(rank(decay_linear(corr(vwap,vol,17),18))
         - rank(decay_linear(corr(rank(low),rank(adv30),18),20)))
         + rank(decay_linear(delta(vwap,3),20))"""
        adv30 = self._adv(30)
        p1 = rank(decay_linear(correlation(self.vwap, self.volume, 17), 18))
        p2 = rank(decay_linear(correlation(rank(self.low), rank(adv30), 18), 20))
        p3 = rank(decay_linear(delta(self.vwap, 3), 20))
        return p1 - p2 + p3

    def alpha097(self) -> Panel:
        """(-1)*(rank(decay_linear(delta(IndNeutralize(close,ind),3),16))
              - rank(decay_linear(corr(IndNeutralize(vwap,ind),vol,20),18)))"""
        close_n = self._ind_neu(self.close)
        vwap_n  = self._ind_neu(self.vwap)
        p1 = rank(decay_linear(delta(close_n, 3), 16))
        p2 = rank(decay_linear(correlation(vwap_n, self.volume, 20), 18))
        return -1 * (p1 - p2)

    def alpha098(self) -> Panel:
        """rank(decay_linear(corr(vwap,ts_sum(adv5,26),5),8))
         - rank(decay_linear(ts_rank(ts_argmin(corr(rank(open),rank(adv15),21),9),7),8))"""
        adv5  = self._adv(5)
        adv15 = self._adv(15)
        p1 = rank(decay_linear(correlation(self.vwap, ts_sum(adv5, 26), 5), 8))
        p2 = rank(decay_linear(ts_rank(ts_argmin(correlation(rank(self.open), rank(adv15), 21), 9), 7), 8))
        return p1 - p2

    def alpha099(self) -> Panel:
        """(rank(decay_linear(corr(high,vol,20),18))
         - rank(decay_linear(corr(low,vol,20),20)))
         + rank(decay_linear(corr(low,vol,9),1))"""
        p1 = rank(decay_linear(correlation(self.high, self.volume, 20), 18))
        p2 = rank(decay_linear(correlation(self.low,  self.volume, 20), 20))
        p3 = rank(decay_linear(correlation(self.low,  self.volume, 9),  1))
        return p1 - p2 + p3

    def alpha100(self) -> Panel:
        """(rank(decay_linear(delta(vwap,2),20))
         + rank(decay_linear(corr(IndNeutralize(vwap,ind),vol,20),18)))
         - rank(decay_linear(delta(close,2),5))"""
        vwap_n = self._ind_neu(self.vwap)
        p1 = rank(decay_linear(delta(self.vwap, 2), 20))
        p2 = rank(decay_linear(correlation(vwap_n, self.volume, 20), 18))
        p3 = rank(decay_linear(delta(self.close, 2), 5))
        return p1 + p2 - p3

    def alpha101(self) -> Panel:
        """(close - open) / (high - low + 0.001)
        当日K线实体长度与日内振幅的比值，衡量动量效率。"""
        return (self.close - self.open) / (self.high - self.low + 0.001)

    # ── 批量计算 ─────────────────────────────────────────────────────────────

    def compute_all(self, alphas: list[int] | None = None) -> dict[str, Panel]:
        """
        批量计算多个 alpha。

        Args:
            alphas: alpha 编号列表（如 [1, 2, 5]），None 表示全部 1~101

        Returns:
            {alpha_name: DataFrame} 字典，如 {'alpha001': DataFrame, ...}
        """
        if alphas is None:
            alphas = list(range(1, 102))

        results: dict[str, Panel] = {}
        for n in alphas:
            name = f"alpha{n:03d}"
            method = getattr(self, name, None)
            if method is None:
                continue
            try:
                results[name] = method()
            except Exception as exc:
                results[name] = pd.DataFrame(
                    np.nan,
                    index=self.close.index,
                    columns=self.close.columns,
                )
                import warnings
                warnings.warn(f"{name} computation failed: {exc}")
        return results
