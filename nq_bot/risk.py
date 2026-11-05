"""Risk engine. Every entry must pass can_enter() and get a size > 0 from size().

Limits: risk per trade (% and $), daily loss, trades/day, consecutive losses,
max contracts, margin utilisation, drawdown kill-switch, post-loss cooldown,
daily profit protection, abnormal-market halt. There is deliberately no way to
scale size up after losses.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import timedelta

log = logging.getLogger("nq_bot.risk")


@dataclass
class DayState:
    date: object = None
    realized: float = 0.0
    peak: float = 0.0
    trades: int = 0
    consecutive_losses: int = 0
    cooldown_until: object = None
    halted_reason: str | None = None


@dataclass
class RiskManager:
    cfg: object
    equity: float
    peak_equity: float = field(init=False)
    killed_reason: str | None = field(default=None, init=False)
    day: DayState = field(default_factory=DayState, init=False)

    def __post_init__(self):
        self.peak_equity = self.equity

    # ---- state -------------------------------------------------------------
    def new_day(self, session_date) -> None:
        if self.day.date != session_date:
            self.day = DayState(date=session_date)

    def halt_day(self, reason: str) -> None:
        if not self.day.halted_reason:
            self.day.halted_reason = reason
            log.warning("HALT (rest of day): %s", reason)

    def kill(self, reason: str) -> None:
        if not self.killed_reason:
            self.killed_reason = reason
            log.error("KILL SWITCH (needs human reset): %s", reason)

    @property
    def drawdown_pct(self) -> float:
        return 0.0 if self.peak_equity <= 0 else 100.0 * (self.peak_equity - self.equity) / self.peak_equity

    # ---- gates -------------------------------------------------------------
    def can_enter(self, now) -> tuple[bool, str]:
        r = self.cfg.risk
        d = self.day
        if self.killed_reason:
            return False, f"killed: {self.killed_reason}"
        if d.halted_reason:
            return False, f"halted: {d.halted_reason}"
        if d.trades >= r.max_trades_per_day:
            return False, "max trades per day reached"
        if d.cooldown_until is not None and now < d.cooldown_until:
            return False, f"cooldown until {d.cooldown_until:%H:%M}"
        return True, "ok"

    def size(self, entry: float, stop: float, spec, margin_per_contract: float,
             commission_per_side: float, slippage_ticks: int) -> tuple[int, str]:
        """Contracts to trade. 0 means 'do not trade' (never rounded up)."""
        r = self.cfg.risk
        stop_pts = abs(entry - stop)
        if stop_pts <= 0 or not math.isfinite(stop_pts):
            return 0, "invalid stop distance"
        per_contract = (stop_pts * spec.point_value
                        + 2 * commission_per_side
                        + 2 * slippage_ticks * spec.tick_value)
        budget = min(self.equity * r.max_risk_per_trade_pct / 100.0, r.max_risk_per_trade_usd)
        # also never risk more than what's left of today's loss allowance
        budget = min(budget, r.max_daily_loss_usd + min(self.day.realized, 0.0))
        by_risk = math.floor(budget / per_contract) if budget > 0 else 0
        by_margin = math.floor(self.equity * r.max_margin_utilization / margin_per_contract)
        qty = max(0, min(by_risk, by_margin, r.max_contracts))
        if qty == 0:
            why = "risk budget" if by_risk == 0 else "margin"
            return 0, f"size 0 ({why}): ${per_contract:.0f} risk/contract vs ${budget:.0f} budget"
        return qty, f"{qty} @ ${per_contract:.0f} risk/contract (budget ${budget:.0f})"

    # ---- updates -----------------------------------------------------------
    def check_open_loss(self, unrealized: float) -> bool:
        """True if open P&L breaches the daily loss limit or the drawdown limit (caller must flatten).
        Checked on every completed bar, so a fast market can overshoot by up to one bar's move."""
        r = self.cfg.risk
        hit = False
        if self.day.realized + unrealized <= -r.max_daily_loss_usd:
            self.halt_day("daily loss limit hit (incl. open P&L)")
            hit = True
        if self.peak_equity > 0:
            dd = 100.0 * (self.peak_equity - (self.equity + unrealized)) / self.peak_equity
            if dd >= r.max_drawdown_pct:
                self.kill(f"max drawdown {dd:.1f}% reached (incl. open P&L)")
                hit = True
        return hit

    # ---- persistence (so a restart can't reset today's limits or the kill switch) ----
    def to_dict(self) -> dict:
        d = self.day
        return {"equity": self.equity, "peak_equity": self.peak_equity, "killed_reason": self.killed_reason,
                "day": {"date": str(d.date) if d.date else None, "realized": d.realized, "peak": d.peak,
                        "trades": d.trades, "consecutive_losses": d.consecutive_losses,
                        "cooldown_until": d.cooldown_until.isoformat() if d.cooldown_until is not None else None,
                        "halted_reason": d.halted_reason}}

    def load_dict(self, s: dict, today) -> None:
        """Restore saved state. Peak equity and the kill switch always carry over; the day's
        counters carry over only if the saved day is `today`."""
        import pandas as pd
        self.peak_equity = max(self.peak_equity, float(s.get("peak_equity", 0.0)))
        self.killed_reason = s.get("killed_reason")
        day = s.get("day") or {}
        if day.get("date") == str(today):
            self.day = DayState(date=today, realized=day["realized"], peak=day["peak"], trades=day["trades"],
                                consecutive_losses=day["consecutive_losses"],
                                cooldown_until=pd.Timestamp(day["cooldown_until"]) if day.get("cooldown_until") else None,
                                halted_reason=day.get("halted_reason"))

    def check_abnormal(self, bar_range: float, atr: float) -> bool:
        if atr and atr > 0 and bar_range > self.cfg.risk.abnormal_range_atr_mult * atr:
            self.halt_day(f"abnormal bar range {bar_range:.1f} pts vs ATR {atr:.1f}")
            return True
        return False

    def record_trade(self, net_pnl: float, now) -> None:
        r = self.cfg.risk
        d = self.day
        d.trades += 1
        d.realized += net_pnl
        d.peak = max(d.peak, d.realized)
        self.equity += net_pnl
        self.peak_equity = max(self.peak_equity, self.equity)

        if net_pnl < 0:
            d.consecutive_losses += 1
            d.cooldown_until = now + timedelta(minutes=r.cooldown_minutes_after_loss)
        else:
            d.consecutive_losses = 0

        if d.realized <= -r.max_daily_loss_usd:
            self.halt_day("daily loss limit")
        if d.consecutive_losses >= r.max_consecutive_losses:
            self.halt_day(f"{d.consecutive_losses} consecutive losses")
        if d.peak >= r.profit_lock_trigger_usd and d.realized <= d.peak * (1 - r.profit_lock_giveback_pct / 100.0):
            self.halt_day("profit protection: gave back too much of today's gain")
        if self.drawdown_pct >= r.max_drawdown_pct:
            self.kill(f"max drawdown {self.drawdown_pct:.1f}% reached")
