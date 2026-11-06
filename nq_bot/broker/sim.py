"""Bar-based paper broker used for backtests and offline paper replay.

Fill model (conservative):
- Orders sent at a bar's close fill at the NEXT bar's open, +/- slippage.
- Stops fill at the stop price -/+ slippage, or at the open if price gapped through.
- Targets are limit orders: fill at the target price, no slippage, only if price trades through by 1 tick.
- If stop and target are both touched in one bar, the stop is assumed to fill first.
- Optional random rejections let you exercise the engine's rejection handling.
"""
from __future__ import annotations

import random

from .base import BracketRequest, Broker, Fill, OrderEvent


class SimBroker(Broker):
    def __init__(self, spec, slippage_ticks: int = 1, reject_prob: float = 0.0, seed: int = 0):
        self.spec = spec
        self.slip = slippage_ticks * spec.tick_size
        self.reject_prob = reject_prob
        self.rng = random.Random(seed)
        self.pos = 0
        self.pending_entry: BracketRequest | None = None
        self.pending_market: list[tuple[int, str, str]] = []  # (signed qty, kind, client_id)
        self.stop: float | None = None
        self.target: float | None = None
        self.prot_qty = 0
        self.client_id = ""
        self._fills: list[Fill] = []
        self._events: list[OrderEvent] = []
        self.connected = True

    # -- Broker API -----------------------------------------------------------
    def submit_bracket(self, req: BracketRequest, ref_price: float) -> None:
        if self.pos != 0 or self.pending_entry is not None:
            self._events.append(OrderEvent(req.client_id, "rejected", "position or entry already working"))
            return
        if self.rng.random() < self.reject_prob:
            self._events.append(OrderEvent(req.client_id, "rejected", "simulated rejection"))
            return
        self.pending_entry = req
        self._events.append(OrderEvent(req.client_id, "submitted"))

    def reduce(self, qty: int, client_id: str) -> None:
        qty = min(qty, abs(self.pos))
        if qty > 0:
            self.pending_market.append((-qty if self.pos > 0 else qty, "reduce", client_id))

    def modify_protection(self, stop: float, qty: int) -> None:
        self.stop, self.prot_qty = stop, qty

    def flatten(self, reason: str) -> None:
        self.pending_entry = None
        self.pending_market = [(-self.pos, "flatten", self.client_id or "flatten")] if self.pos else []
        self.stop = self.target = None

    def flatten_now(self, price, ts) -> None:
        """Emergency exit at the last known price (paper only): cancel everything, close at market now."""
        self.pending_entry = None
        self.pending_market = []
        if self.pos != 0 and price is not None:
            long = self.pos > 0
            px = price - self.slip if long else price + self.slip
            self._fill("flatten", -self.pos, px, ts)
        self.stop = self.target = None

    def position(self) -> int:
        return self.pos

    def has_working_entry(self) -> bool:
        return self.pending_entry is not None

    def poll(self):
        f, e = self._fills, self._events
        self._fills, self._events = [], []
        return f, e

    def is_connected(self) -> bool:
        return self.connected

    # -- simulation step ------------------------------------------------------
    def _fill(self, kind, signed_qty, price, ts):
        price = self.spec.round_to_tick(price)
        self.pos += signed_qty
        self._fills.append(Fill(self.client_id, kind, 1 if signed_qty > 0 else -1, abs(signed_qty), price, ts))
        if self.pos == 0:
            self.stop = self.target = None
            self.prot_qty = 0

    def process_bar(self, ts, o, h, l, c) -> None:
        # 1) market orders queued at the previous close
        for signed, kind, cid in self.pending_market:
            px = o + self.slip if signed > 0 else o - self.slip
            self._fill(kind, signed, px, ts)
        self.pending_market = []

        # 2) new entry
        if self.pending_entry is not None:
            req = self.pending_entry
            self.pending_entry = None
            self.client_id = req.client_id
            px = o + self.slip if req.side > 0 else o - self.slip
            # entry would already be beyond the stop -> treat as rejected by risk check at broker
            if (req.side > 0 and px <= req.stop) or (req.side < 0 and px >= req.stop):
                self._events.append(OrderEvent(req.client_id, "cancelled", "gapped through stop before entry"))
            else:
                self._fill("entry", req.side * req.qty, px, ts)
                self.stop, self.target, self.prot_qty = req.stop, req.target, req.qty

        # 3) protective orders
        if self.pos != 0 and self.stop is not None:
            long = self.pos > 0
            qty = abs(self.pos)
            stop_hit = l <= self.stop if long else h >= self.stop
            tgt_hit = (h >= self.target + self.spec.tick_size) if long else (l <= self.target - self.spec.tick_size)
            if stop_hit:
                base = min(self.stop, o) if long else max(self.stop, o)
                px = base - self.slip if long else base + self.slip
                self._fill("stop", -qty if long else qty, px, ts)
            elif tgt_hit:
                self._fill("target", -qty if long else qty, self.target, ts)
