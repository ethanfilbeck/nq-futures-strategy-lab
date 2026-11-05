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


def _last_price(b: IBKRBroker) -> float:
    [tk] = b.ib.reqTickers(b.contract)
    for px in (tk.last, tk.close, tk.marketPrice()):
        if px and px == px and px > 0:
            return float(px)
    raise SystemExit("No market price available - check your CME market-data subscription.")


def run(cfg, action: str, side: str = "buy", stop: float | None = None) -> None:
    b = _connect(cfg)
    try:
        if action == "status":
            _show(b)
        elif action in ("bracket", "duplicate"):
            if action == "bracket" and (b.position() != 0 or b.has_working_entry()):
                raise SystemExit("Already in a position - run `drill flatten` first.")
            sgn = 1 if side == "buy" else -1
            ref = _last_price(b)
            spec = b.spec
            req = BracketRequest(f"drill-{int(time.time())}", sgn, 1,
                                 stop=spec.round_to_tick(ref - sgn * STOP_PTS),
                                 target=spec.round_to_tick(ref + sgn * TARGET_PTS))
            # for "duplicate" a position already exists, so the adapter must reject this
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
            b.poll()  # runs _reconcile_protection(): resize / replace / cancel orphans
            b.ib.sleep(2)
            _, events = b.poll()
            for e in events:
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
