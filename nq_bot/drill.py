"""Paper-trading drills: exercise the IBKR adapter's safety mechanics with 1 MNQ on a PAPER account.

These test the software, not profitability. Always paper: the adapter refuses non-paper
ports and non-DU accounts, and this module never authorises live trading.

  python cli.py drill status                    # contract, position, working orders (read-only)
  python cli.py drill bracket --side buy        # 1 MNQ entry + server-side stop/target, waits for fill
  python cli.py drill duplicate                 # tries to send a 2nd entry while one exists -> must be rejected
  python cli.py drill reconcile --stop 21000    # repair protection to match the real position
  python cli.py drill flatten                   # cancel everything and close at market
"""
from __future__ import annotations

import time

from .broker.base import BracketRequest
from .broker.ibkr import IBKRBroker
from .contracts import SPECS

STOP_PTS, TARGET_PTS = 20.0, 40.0
# With --delayed (no CME real-time subscription) the reference price can be ~10 minutes old, so the
# entry limit, stop and target are placed far enough away that a stale price can't put them on the
# wrong side of the market. Paper drills only - the live runner never uses delayed data.
DELAYED_BUFFER_PTS, DELAYED_STOP_PTS, DELAYED_TARGET_PTS = 150.0, 150.0, 300.0


def _connect(cfg) -> IBKRBroker:
    if cfg.mode != "paper":
        raise SystemExit("Drills only run with mode: paper.")
    b = IBKRBroker(cfg, SPECS[cfg.instrument.root], live_authorized=False)
    b.connect(startup_checks=False)
    return b


def _show(b: IBKRBroker) -> None:
    print(f"Contract: {b.contract.localSymbol}  (front month by our calendar: {b.front.local_symbol}, "
          f"roll on/after {b.front.roll_date})")
    print(f"Position: {b.position():+d}")
    trades = [t for t in b.ib.openTrades() if t.contract.symbol in ("NQ", "MNQ")]
    if not trades:
        print("Working orders: none")
    for t in trades:
        o = t.order
        px = o.auxPrice if o.orderType == "STP" else o.lmtPrice
        print(f"  #{o.orderId} {t.contract.localSymbol} {o.action} {o.totalQuantity:g} {o.orderType} @ {px} "
              f"[{t.orderStatus.status}] ref={o.orderRef}")


def _good(px) -> bool:
    return bool(px) and px == px and px > 0


def _last_price(b: IBKRBroker, delayed: bool = False, timeout: float = 15.0) -> float:
    if not delayed:
        [tk] = b.ib.reqTickers(b.contract)
        for px in (tk.last, tk.close, tk.marketPrice()):
            if _good(px):
                return float(px)
        raise SystemExit("No market price available - check your CME market-data subscription.")
    # Delayed quotes: a snapshot request can hang, so stream for up to `timeout` seconds instead.
    tk = b.ib.reqMktData(b.contract, "", False, False)
    try:
        waited = 0.0
        while waited < timeout:
            b.ib.sleep(0.5)
            waited += 0.5
            for px in (tk.last, tk.marketPrice(), tk.close):
                if _good(px):
                    print(f"Delayed reference price: {float(px)}")
                    return float(px)
    finally:
        b.ib.cancelMktData(b.contract)
    # Fallback: the latest 1-minute bar from IB's historical-data service.
    try:
        bars = b.ib.reqHistoricalData(b.contract, "", "1800 S", "1 min", "TRADES", False, timeout=15)
        if bars and _good(bars[-1].close):
            print(f"Reference price from IB's last 1-min bar ({bars[-1].date}): {bars[-1].close}")
            return float(bars[-1].close)
    except Exception as e:  # noqa: BLE001 - any failure here just means "no price"
        print(f"Historical-bar fallback failed: {e}")
    raise SystemExit("No delayed price arrived - nothing was ordered. Re-run with --ref <price> using the "
                     "MNQ price from your TradingView chart.")


def run(cfg, action: str, side: str = "buy", stop: float | None = None, delayed: bool = False,
        ref: float | None = None) -> None:
    b = _connect(cfg)
    if delayed:
        b.ib.reqMarketDataType(3)   # IB's free 10-15 min delayed quotes
        print("Using DELAYED market data (paper drill only): wide stop/target buffers.")
    try:
        if action == "status":
            _show(b)
        elif action in ("bracket", "duplicate"):
            if action == "bracket" and (b.position() != 0 or b.has_working_entry()):
                raise SystemExit("Already in a position - run `drill flatten` first.")
            sgn = 1 if side == "buy" else -1
            if ref is not None:
                if not delayed:
                    raise SystemExit("--ref needs --delayed (it uses the wide buffers).")
                print(f"Using the reference price you typed: {ref}")
            else:
                ref = _last_price(b, delayed)
            spec = b.spec
            sp, tp = (DELAYED_STOP_PTS, DELAYED_TARGET_PTS) if delayed else (STOP_PTS, TARGET_PTS)
            offset = int(DELAYED_BUFFER_PTS / spec.tick_size) if delayed else 4
            req = BracketRequest(f"drill-{int(time.time())}", sgn, 1,
                                 stop=spec.round_to_tick(ref - sgn * sp),
                                 target=spec.round_to_tick(ref + sgn * tp),
                                 limit_offset_ticks=offset)
            # for "duplicate" a position already exists, so the adapter must reject this
            b.adopt_existing_orders()   # know about the working stop/target before polling
            b.submit_bracket(req, ref)
            for _ in range(30):
                b.ib.sleep(1)
                fills, events = b.poll()
                for e in events:
                    print(f"EVENT {e.status}: {e.message}")
                for f in fills:
                    print(f"FILL {f.kind} {'BUY' if f.side > 0 else 'SELL'} {f.qty} @ {f.price}")
                if action == "duplicate" or b.position() != 0:
                    break
            _show(b)
        elif action == "reconcile":
            b.adopt_existing_orders()
            if stop is not None:
                b.stop_px = stop
            _, events = b.poll()  # runs _reconcile_protection(): resize / replace / cancel orphans
            b.ib.sleep(2)
            _, more = b.poll()
            for e in events + more:
                print(f"EVENT {e.status}: {e.message}")
            _show(b)
        elif action == "flatten":
            b.flatten("drill")
            b.ib.sleep(3)
            _show(b)
        else:
            raise SystemExit(f"unknown drill action {action}")
    finally:
        b.ib.disconnect()
