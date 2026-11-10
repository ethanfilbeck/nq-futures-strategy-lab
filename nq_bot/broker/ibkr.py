"""Interactive Brokers adapter (ib_async) - PAPER by default.

Safety interlocks:
- Refuses non-paper ports unless live is explicitly authorised.
- Refuses to run unless every managed account starts with 'DU' (IB paper accounts) when in paper mode.
- Qualifies the actual quarterly contract (e.g. MNQZ6); never orders a continuous symbol.
- Protective stop + target are sent as an IB bracket (OCA) attached to the entry, so they live on
  IB's servers and keep protecting the position if this program crashes or disconnects.

NOT exercised in the build environment (no TWS there). Test it against your paper account.
"""
from __future__ import annotations

import logging
import time
from datetime import date as date_type
from typing import TYPE_CHECKING

import pandas as pd

from ..contracts import front_month
from .base import BracketRequest, Broker, Fill, OrderEvent

if TYPE_CHECKING:          # type checking only; ib_async is imported lazily at runtime
    from ib_async import IB, Contract, Trade

    from ..config import Cfg
    from ..contracts import ContractSpec, FrontMonth

log = logging.getLogger("nq_bot.ibkr")
PAPER_PORTS = {7497, 4002}
ENTRY_TIMEOUT_SEC = 90


class IBKRBroker(Broker):
    def __init__(self, cfg: Cfg, spec: ContractSpec, live_authorized: bool = False):
        from ib_async import IB  # pip install ib_async

        self.cfg, self.spec, self.live = cfg, spec, live_authorized
        if not live_authorized and cfg.ibkr.port not in PAPER_PORTS:
            raise RuntimeError(f"Port {cfg.ibkr.port} is not a paper port {sorted(PAPER_PORTS)}; refusing.")
        self.ib: IB = IB()
        self._contract: Contract | None = None          # set by connect(); use the `contract` property
        self.entry: Trade | None = None
        self.tp: Trade | None = None
        self.sl: Trade | None = None
        self.entry_sent_at = 0.0
        self.kind_by_order: dict[int, str] = {}
        self.cid_by_order: dict[int, str] = {}
        self.seen_execs: set[str] = set()
        self._events: list[OrderEvent] = []
        self._reported_dead: set[int] = set()
        self.reducing: list[Trade] = []        # working reduce/flatten market orders
        self.stop_px: float | None = None
        self.front: FrontMonth | None = None

    @property
    def contract(self) -> Contract:
        """The qualified front-month contract. Raises rather than sending an order to nothing."""
        if self._contract is None:
            raise RuntimeError("Not connected to IB: call connect() before trading.")
        return self._contract

    @contract.setter
    def contract(self, c: Contract) -> None:
        self._contract = c

    # ---------------------------------------------------------------- setup
    def connect(self, startup_checks: bool = True):
        from ib_async import Future

        c = self.cfg.ibkr
        self.ib.connect(c.host, c.port, clientId=c.client_id, timeout=15)
        accounts = self.ib.managedAccounts()
        if not self.live and not all(a.startswith("DU") for a in accounts):
            self.ib.disconnect()
            raise RuntimeError("Connected account is not an IB paper account (DU...). Refusing in paper mode.")
        from datetime import date
        fm = front_month(self.cfg.instrument.root, date.today(), self.cfg.instrument.roll_days_before_expiry)
        fut = Future(symbol=self.cfg.instrument.root, lastTradeDateOrContractMonth=fm.contract_month,
                     exchange=self.cfg.instrument.exchange, currency="USD")
        q = self.ib.qualifyContracts(fut)
        if not q:
            raise RuntimeError(f"Could not qualify {fm.local_symbol}")
        self._contract = q[0]
        if self.contract.localSymbol != fm.local_symbol:
            raise RuntimeError(f"Expected {fm.local_symbol}, broker returned {self.contract.localSymbol}")
        mult = float(self.contract.multiplier or 0)
        if mult and abs(mult - self.spec.point_value) > 1e-9:
            raise RuntimeError(f"Multiplier mismatch: broker {mult} vs spec {self.spec.point_value}")
        self.front = fm
        if startup_checks:
            self._startup_checks()
        log.info("Trading %s (expiry %s, roll by %s) on accounts %s", fm.local_symbol, fm.expiry, fm.roll_date, accounts)
        return fm

    def _startup_checks(self):
        """Refuse to start with ANY Nasdaq-100 futures position or working order, in any contract
        month - this catches a position left over in the old month after a roll."""
        family = {"NQ", "MNQ"}
        stray_pos = [f"{p.contract.localSymbol} {p.position:+g}" for p in self.ib.positions()
                     if p.contract.symbol in family and p.position != 0]
        if stray_pos:
            raise RuntimeError(f"Existing NQ/MNQ positions: {stray_pos}. Close them manually before starting.")
        self.ib.reqAllOpenOrders()
        self.ib.sleep(1)
        stray_ord = [f"{t.contract.localSymbol} {t.order.action} {t.order.totalQuantity:g} {t.order.orderType}"
                     for t in self.ib.openTrades() if t.contract.symbol in family]
        if stray_ord:
            raise RuntimeError(f"Working NQ/MNQ orders exist: {stray_ord}. Cancel them manually before starting.")

    def adopt_existing_orders(self) -> None:
        """After a restart: treat working stop/limit orders that close the current position as ours,
        so reconciliation resizes them instead of stacking a second stop."""
        pos = self.position()
        if pos == 0:
            return
        for t in self.ib.openTrades():
            if t.contract.conId != self.contract.conId:
                continue
            o = t.order
            if (pos > 0 and o.action != "SELL") or (pos < 0 and o.action != "BUY"):
                continue
            ref = o.orderRef or "adopted"
            if o.orderType == "STP" and (self.sl is None or self.sl.isDone()):
                if o.auxPrice is None:          # a stop with no price protects nothing - leave it alone
                    log.warning("Ignoring a working STP order with no stop price (orderRef %s)", ref)
                    continue
                self.sl, self.stop_px = self._track(t, "stop", ref), float(o.auxPrice)
            elif o.orderType == "LMT" and (self.tp is None or self.tp.isDone()):
                self.tp = self._track(t, "target", ref)

    def roll_due(self, today: date_type) -> bool:
        """True once `today` maps to a different quarterly contract than the one we connected to."""
        if self.front is None:
            raise RuntimeError("Not connected to IB: call connect() before checking the roll date.")
        fm = front_month(self.cfg.instrument.root, today, self.cfg.instrument.roll_days_before_expiry)
        return fm.local_symbol != self.front.local_symbol

    def net_liquidation(self) -> float:
        for v in self.ib.accountSummary():
            if v.tag == "NetLiquidation" and v.currency == "USD":
                return float(v.value)
        raise RuntimeError("NetLiquidation not available")

    def stream_bars(self):
        return self.ib.reqHistoricalData(self.contract, endDateTime="", durationStr="10 D", barSizeSetting="1 min",
                                         whatToShow="TRADES", useRTH=False, formatDate=2, keepUpToDate=True)

    # ---------------------------------------------------------------- orders
    def _track(self, trade, kind, cid):
        self.kind_by_order[trade.order.orderId] = kind
        self.cid_by_order[trade.order.orderId] = cid
        return trade

    def submit_bracket(self, req: BracketRequest, ref_price: float) -> None:
        if self.position() != 0 or self.has_working_entry():
            self._events.append(OrderEvent(req.client_id, "rejected", "position or entry already working"))
            return
        action = "BUY" if req.side > 0 else "SELL"
        limit = self.spec.round_to_tick(ref_price + req.side * req.limit_offset_ticks * self.spec.tick_size)
        bo = self.ib.bracketOrder(action, req.qty, limitPrice=limit,
                                  takeProfitPrice=req.target, stopLossPrice=req.stop)
        for o in bo:
            o.orderRef = req.client_id
            o.tif = "DAY"
        self.entry = self._track(self.ib.placeOrder(self.contract, bo.parent), "entry", req.client_id)
        self.tp = self._track(self.ib.placeOrder(self.contract, bo.takeProfit), "target", req.client_id)
        self.sl = self._track(self.ib.placeOrder(self.contract, bo.stopLoss), "stop", req.client_id)
        self.entry_sent_at = time.time()
        self.stop_px = req.stop
        self._events.append(OrderEvent(req.client_id, "submitted", f"limit {limit} stop {req.stop} tgt {req.target}"))

    def reduce(self, qty: int, client_id: str) -> None:
        from ib_async import MarketOrder

        pos = self.position()
        qty = min(qty, abs(pos))
        if qty <= 0:
            return
        o = MarketOrder("SELL" if pos > 0 else "BUY", qty)
        o.orderRef, o.tif = client_id, "DAY"   # explicit TIF avoids IB warning 10349 (false "Cancelled")
        self.reducing.append(self._track(self.ib.placeOrder(self.contract, o), "reduce", client_id))

    def modify_protection(self, stop: float, qty: int) -> None:
        self.stop_px = stop
        if self.sl is not None and qty > 0:
            self.sl.order.auxPrice = stop
            self.sl.order.totalQuantity = qty
            self.ib.placeOrder(self.contract, self.sl.order)
        if self.tp is not None and qty > 0:
            self.tp.order.totalQuantity = qty
            self.ib.placeOrder(self.contract, self.tp.order)

    def flatten(self, reason: str) -> None:
        from ib_async import MarketOrder

        for t in self.ib.openTrades():
            if t.contract.conId == self.contract.conId:
                self.ib.cancelOrder(t.order)
        self.ib.sleep(1)
        pos = self.position()
        if pos != 0:
            o = MarketOrder("SELL" if pos > 0 else "BUY", abs(pos))
            o.orderRef, o.tif = f"flatten:{reason[:20]}", "DAY"  # avoid 10349 false "Cancelled" status
            self.reducing.append(self._track(self.ib.placeOrder(self.contract, o), "flatten",
                                             self.entry.order.orderRef if self.entry else "flatten"))
        self.entry = self.tp = self.sl = None
        self.stop_px = None

    # ---------------------------------------------------------------- state
    def position(self) -> int:
        return int(sum(p.position for p in self.ib.positions() if p.contract.conId == self.contract.conId))

    def has_working_entry(self) -> bool:
        return self.entry is not None and not self.entry.isDone() and self.entry.orderStatus.filled == 0

    def is_connected(self) -> bool:
        return self.ib.isConnected()

    def poll(self):
        fills = []
        for f in self.ib.fills():
            ex = f.execution
            if f.contract.conId != self.contract.conId or ex.execId in self.seen_execs:
                continue
            self.seen_execs.add(ex.execId)
            kind = self.kind_by_order.get(ex.orderId)
            if kind is None:
                continue  # not ours (manual trade) - position() mismatch will trip a halt in the engine
            ts = pd.Timestamp(f.time)
            ts = (ts.tz_localize("UTC") if ts.tz is None else ts).tz_convert(self.cfg.session.timezone)
            fills.append(Fill(self.cid_by_order[ex.orderId], kind, 1 if ex.side == "BOT" else -1,
                              int(ex.shares), float(ex.price), ts))
        # entry that never filled -> cancel the whole bracket (prevents stale entries)
        if self.entry is not None and self.entry.orderStatus.filled == 0 and not self.entry.isDone() \
                and time.time() - self.entry_sent_at > ENTRY_TIMEOUT_SEC:
            self.ib.cancelOrder(self.entry.order)
            self._events.append(OrderEvent(self.entry.order.orderRef, "cancelled", "entry not filled in time"))
            self.entry = self.tp = self.sl = None
        # rejected / cancelled entries
        if self.entry is not None and self.entry.order.orderId not in self._reported_dead:
            st = self.entry.orderStatus.status
            if st in ("Cancelled", "ApiCancelled", "Inactive") and self.entry.orderStatus.filled == 0:
                msg = "; ".join(e.message for e in self.entry.log if e.message)[-200:]
                self._events.append(OrderEvent(self.entry.order.orderRef, "rejected", f"{st}: {msg}"))
                self._reported_dead.add(self.entry.order.orderId)
                self.entry = self.tp = self.sl = None
        # entry partly filled and the rest is stuck -> cancel the remainder; reconcile below
        # then makes sure the stop covers exactly what we hold
        if self.entry is not None and not self.entry.isDone() and self.entry.orderStatus.filled > 0 \
                and time.time() - self.entry_sent_at > ENTRY_TIMEOUT_SEC:
            self.ib.cancelOrder(self.entry.order)
            self._events.append(OrderEvent(self.entry.order.orderRef, "partial",
                                           f"entry filled {self.entry.orderStatus.filled:g}, remainder cancelled"))
        if self.contract is not None:
            self._reconcile_protection()
        ev, self._events = self._events, []
        return fills, ev

    def _reconcile_protection(self):
        pos = self.position()
        if pos != 0 and (self.sl is None or self.sl.isDone()):
            # Never treat a position as unprotected just because THIS session didn't place the stop
            # (e.g. after a restart): adopt a working stop/target at IB before deciding anything.
            self.adopt_existing_orders()
        entry_working = self.entry is not None and not self.entry.isDone()
        sl = self.sl if (self.sl is not None and not self.sl.isDone()) else None
        action = protection_fix(pos, entry_working, sl is not None, int(sl.order.totalQuantity) if sl else 0,
                                any(not t.isDone() for t in self.reducing))
        if action == "none":
            return
        from ib_async import StopOrder
        ref = self.sl.order.orderRef if self.sl is not None else "protect"
        if action == "cancel_children":
            for t in (self.sl, self.tp):
                if t is not None and not t.isDone():
                    self.ib.cancelOrder(t.order)
            self.sl = self.tp = None
        elif action == "resize":
            # the working stop's own price is the fallback, so a resize can never send a stop with no level
            level = self.stop_px
        if level is None and sl is not None and sl.order.auxPrice is not None:
            level = float(sl.order.auxPrice)
            if level is None:
                self._events.append(OrderEvent(ref, "rejected", "cannot resize a stop with no known level - flattening"))
                self.flatten("unprotected position")
                return
            self.modify_protection(level, abs(pos))
        elif action == "replace_stop":
            if self.stop_px is None:  # no known stop level -> can't protect -> get out
                self._events.append(OrderEvent(ref, "rejected", "unprotected position with no stop level - flattening"))
                self.flatten("unprotected position")
                return
            o = StopOrder("SELL" if pos > 0 else "BUY", abs(pos), self.stop_px)
            o.orderRef, o.tif = ref, "DAY"
            self.sl = self._track(self.ib.placeOrder(self.contract, o), "stop", self.cid_by_order.get(
                self.entry.order.orderId, ref) if self.entry else ref)
            if self.tp is not None and not self.tp.isDone():
                self.tp.order.totalQuantity = abs(pos)
                self.ib.placeOrder(self.contract, self.tp.order)
        self._events.append(OrderEvent(ref, "protection", f"{action}: position {pos}, stop {self.stop_px}"))


def protection_fix(pos: int, entry_working: bool, sl_live: bool, sl_qty: int, reduce_working: bool) -> str:
    """Decide how to make the protective stop match the real position. Pure function (unit-tested)."""
    if pos == 0:
        return "cancel_children" if sl_live and not entry_working else "none"
    if reduce_working:
        return "none"          # wait for the reduce to finish; we'll check again next poll
    if not sl_live:
        return "replace_stop"  # open position with no working stop - never allowed
    if sl_qty != abs(pos):
        return "resize"
    return "none"
