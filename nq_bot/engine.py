"""Trading engine: data -> regime -> strategy -> risk -> execution -> position management.

The same engine runs in backtests (SimBroker), offline paper replay, and IBKR paper.
Call `on_bar(ts, row)` once per COMPLETED 1-minute bar, after the broker has had the
chance to report fills for that bar.
"""
from __future__ import annotations

import math

from .broker.base import BracketRequest
from .features import _hm
from .regime import classify
from .risk import RiskManager
from .strategy import OpeningRangeBreakout


class Engine:
    def __init__(self, cfg, broker, spec, journal, alerts, events, starting_equity=None):
        self.cfg = cfg
        self.broker = broker
        self.spec = spec
        self.journal = journal
        self.alerts = alerts
        self.events = events
        self.risk = RiskManager(cfg, starting_equity or cfg.risk.starting_equity)
        if cfg.strategy.name == "intraday_momentum":
            from .momentum import IntradayMomentum
            self.strategy = IntradayMomentum(cfg, spec)
        elif cfg.strategy.name == "sweep":
            from .family2 import LiquiditySweep
            self.strategy = LiquiditySweep(cfg, spec)
        elif cfg.strategy.name == "vwap_pullback":
            from .family2 import VwapPullback
            self.strategy = VwapPullback(cfg, spec)
        elif cfg.strategy.name == "tradingview":
            from .external import ExternalSignals
            self.strategy = ExternalSignals(cfg, spec)  # signals from TradingView webhooks, same risk engine
        elif cfg.strategy.name == "none":
            self.strategy = None  # monitor only: data, risk and reporting run, no entries
        else:
            self.strategy = OpeningRangeBreakout(cfg, spec)
        self.flatten_minute = _hm(cfg.session.flatten_time)
        self.cps = cfg.instrument.commission_per_side
        self.trade = None
        self.trades: list[dict] = []
        self.pending = None  # (client_id, signal) awaiting broker confirmation
        self.seq = 0
        self.entries_from = None

    # ---------------------------------------------------------------- fills
    def sync_broker(self, now) -> None:
        fills, events = self.broker.poll()
        for ev in events:
            self.journal.write(now, "order_event", client_id=ev.client_id, status=ev.status, msg=ev.message)
            if ev.status in ("rejected", "cancelled") and self.pending and ev.client_id == self.pending[0]:
                self.alerts.send("warning", f"Entry {ev.status}: {ev.message}")
                self.pending = None
        for f in fills:
            self._apply_fill(f)

    def _apply_fill(self, f) -> None:
        if f.kind == "entry":
            sig = self.pending[1] if self.pending else None
            self.pending = None
            if self.trade is None:
                self.trade = {
                    "id": f.client_id, "side": f.side, "qty": f.qty, "open_qty": f.qty,
                    "entry_price": f.price, "entry_ts": f.ts,
                    "stop": sig.stop if sig else None, "target": sig.target if sig else None,
                    "partial": sig.partial_target if sig else None, "partial_done": False,
                    "regime": sig.regime if sig else "unknown", "exits": [],
                    "commission": f.qty * self.cps,
                }
            else:  # additional partial fill of the entry
                t = self.trade
                t["entry_price"] = (t["entry_price"] * t["qty"] + f.price * f.qty) / (t["qty"] + f.qty)
                t["qty"] += f.qty
                t["open_qty"] += f.qty
                t["commission"] += f.qty * self.cps
            self.journal.write(f.ts, "fill", **vars(f))
            self.alerts.send("info", f"ENTRY {'LONG' if f.side > 0 else 'SHORT'} {f.qty} @ {f.price}")
            return

        t = self.trade
        if t is None:  # fill with no known trade: trust the broker, flatten, and stop
            self.alerts.send("error", f"Unexpected {f.kind} fill with no tracked trade - flattening")
            self.broker.flatten("unexpected fill")
            self.risk.halt_day("unexpected fill / position mismatch")
            return
        t["exits"].append((f.qty, f.price, f.kind, f.ts))
        t["open_qty"] -= f.qty
        t["commission"] += f.qty * self.cps
        self.journal.write(f.ts, "fill", **vars(f))
        if t["open_qty"] <= 0:
            self._close_trade(f.ts)

    def _close_trade(self, ts) -> None:
        t = self.trade
        pv = self.spec.point_value
        gross = sum(t["side"] * (px - t["entry_price"]) * q * pv for q, px, _, _ in t["exits"])
        net = gross - t["commission"]
        risk_pts = abs(t["entry_price"] - t["stop"]) if t["stop"] else float("nan")
        rec = {
            "id": t["id"], "side": t["side"], "qty": t["qty"], "entry_ts": t["entry_ts"], "exit_ts": ts,
            "entry_price": t["entry_price"], "exit_price": t["exits"][-1][1], "exit_kind": t["exits"][-1][2],
            "gross": round(gross, 2), "commission": round(t["commission"], 2), "net": round(net, 2),
            "r_multiple": round(net / (risk_pts * pv * t["qty"]), 3) if risk_pts and risk_pts == risk_pts else None,
            "regime": t["regime"], "entry_hour": t["entry_ts"].hour,
        }
        self.trades.append(rec)
        self.risk.record_trade(net, ts)
        self.trade = None
        self.journal.write(ts, "trade_closed", **rec)
        self.alerts.send("info" if net >= 0 else "warning", f"CLOSED {rec['exit_kind']} net ${net:,.2f}")
        if self.risk.killed_reason or self.risk.day.halted_reason:
            self.alerts.send("error", f"Trading stopped: {self.risk.killed_reason or self.risk.day.halted_reason}")

    # ---------------------------------------------------------------- bars
    def on_bar(self, ts, row) -> None:
        self.sync_broker(ts)
        self.risk.new_day(row["session_date"])
        if self.strategy is not None and hasattr(self.strategy, "observe"):
            self.strategy.observe(row)  # strategies that track state on every bar (e.g. sweeps)

        if not self.broker.is_connected():
            self.risk.halt_day("broker disconnected")
            self.alerts.send("error", "Broker disconnected - no new entries")
            return

        atr = row["atr"]
        if isinstance(atr, float) and not math.isnan(atr) and self.risk.check_abnormal(row["bar_range"], atr):
            self._flatten(ts, "abnormal market")
            return

        if self.trade is not None or self.broker.position() != 0:
            self._manage(ts, row)
            return
        self._maybe_enter(ts, row)

    def _flatten(self, ts, reason: str) -> None:
        if self.broker.position() != 0 or self.broker.has_working_entry() or self.pending:
            self.broker.flatten(reason)
            self.journal.write(ts, "flatten", reason=reason)
            self.alerts.send("warning", f"FLATTEN: {reason}")
        self.pending = None

    def _manage(self, ts, row) -> None:
        t = self.trade
        if t is None:  # broker shows a position we don't track
            self.alerts.send("error", "Position mismatch - flattening")
            self.risk.halt_day("position mismatch")
            self._flatten(ts, "position mismatch")
            return
        pv = self.spec.point_value
        unreal = t["side"] * (row["close"] - t["entry_price"]) * t["open_qty"] * pv
        if self.risk.check_open_loss(unreal):
            self._flatten(ts, self.risk.killed_reason or self.risk.day.halted_reason or "loss limit")
            return
        if row["minute_of_day"] >= self.flatten_minute or not row["rth"]:
            self._flatten(ts, "end of session")
            return
        ev = self.events.high_impact_soon(ts) if self.cfg.events.flatten_before_high_impact else None
        if ev:
            self._flatten(ts, f"high-impact event: {ev}")
            return
        if self.risk.killed_reason:
            self._flatten(ts, self.risk.killed_reason)
            return

        s = self.cfg.strategy
        if not t["partial_done"] and t["partial"] is not None and t["open_qty"] >= 2:
            hit = row["high"] >= t["partial"] if t["side"] > 0 else row["low"] <= t["partial"]
            if hit:
                q = max(1, int(t["open_qty"] * s.partial_fraction))
                self.broker.reduce(q, t["id"])
                t["partial_done"] = True
                remaining = t["open_qty"] - q
                if s.move_stop_to_breakeven and remaining > 0:
                    be = self.spec.round_to_tick(t["entry_price"])
                    self.broker.modify_protection(be, remaining)
                    t["stop_moved_to"] = be
                self.journal.write(ts, "partial", qty=q, level=t["partial"])

    def _maybe_enter(self, ts, row) -> None:
        if self.strategy is None:
            return
        if self.entries_from is not None and ts < self.entries_from:
            return  # warm-up period: indicators and risk run, no entries
        if self.pending or self.broker.has_working_entry():
            return  # duplicate-order guard
        regime = classify(row, self.cfg)
        sig = self.strategy.evaluate(row, regime)
        if sig is None:
            return
        ev = self.events.blackout(ts)
        if ev:
            self.journal.write(ts, "skip", reason=f"event blackout: {ev}", signal=vars(sig))
            return
        ok, why = self.risk.can_enter(ts)
        if not ok:
            self.journal.write(ts, "skip", reason=why, signal=vars(sig))
            return
        qty, note = self.risk.size(sig.entry_ref, sig.stop, self.spec, self.cfg.instrument.margin_per_contract,
                                   self.cps, self.cfg.instrument.slippage_ticks)
        if qty <= 0:
            self.journal.write(ts, "skip", reason=note, signal=vars(sig))
            return
        if not (1 <= qty <= self.cfg.risk.max_contracts) or int(qty) != qty:
            self.journal.write(ts, "skip", reason=f"order quantity {qty} outside limits", signal=vars(sig))
            self.alerts.send("error", f"Refused order with invalid quantity {qty}")
            return
        if (sig.side > 0 and not sig.stop < sig.entry_ref < sig.target) or \
           (sig.side < 0 and not sig.target < sig.entry_ref < sig.stop):
            self.journal.write(ts, "skip", reason="stop/target on the wrong side of entry", signal=vars(sig))
            return
        self.seq += 1
        cid = f"{row['session_date']}-{self.seq}"
        self.pending = (cid, sig)
        self.strategy.mark_traded(row["session_date"], sig.side)
        self.journal.write(ts, "order", client_id=cid, qty=qty, sizing=note, signal=vars(sig))
        self.broker.submit_bracket(BracketRequest(cid, sig.side, qty, sig.stop, sig.target), sig.entry_ref)
