"""Forward paper tracking of H8 (pre-FOMC drift) on an IB PAPER account.

Rules = docs/PREREG_FAMILY3.md, H8, unchanged: buy 1 MNQ at 14:00 ET on the trading day before a scheduled
FOMC statement, 3% protective stop (GTC, held at IB so it survives overnight and restarts), sell at 13:55 ET
on statement day. Paper only: IBKRBroker refuses live ports and non-DU accounts; there is no live switch here.

Results go to logs/fomc_paper/forward_trades.jsonl - forward paper results, kept apart from backtests.

    py cli.py fomc-paper              # waits for the next event, trades it, exits
    py cli.py fomc-paper --test-now   # plumbing check: buy, place the GTC stop, sell ~20 s later (logged separately)

Phone alerts: if ALERT_WEBHOOK_URL (a Discord webhook) is set in .env, it posts on entry, exit, stop-out, a
re-placed stop, lost/restored connection, a refused or skipped trade, and any crash. `py cli.py alert-test` checks it.
"""
from __future__ import annotations

import csv
import json
import logging
import time
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

log = logging.getLogger("nq_bot.fomc_paper")
TZ = "America/New_York"
ENTRY_HM, EXIT_HM = (14, 0), (13, 55)
ENTRY_GRACE_MIN = 5          # enter only 14:00-14:05 ET; later than that = skip (rules say 14:00)
STOP_FRAC = 0.03
REF = "fomc-paper"
OUT = Path("logs/fomc_paper")


# ---------------------------------------------------------------- schedule (pure, unit-tested)
def fomc_events(path="config/events.csv") -> list[date]:
    out = []
    with open(path) as f:
        for row in csv.reader(line for line in f if not line.startswith("#")):
            if len(row) >= 2 and "FOMC" in row[1]:
                out.append(pd.Timestamp(row[0]).date())
    return sorted(out)


def prev_weekday(d: date) -> date:
    d -= timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


@dataclass
class Window:
    event: date
    entry: pd.Timestamp
    exit: pd.Timestamp


def window_for(event: date) -> Window:
    p = prev_weekday(event)
    return Window(event, pd.Timestamp(p.isoformat(), tz=TZ).replace(hour=ENTRY_HM[0], minute=ENTRY_HM[1]),
                  pd.Timestamp(event.isoformat(), tz=TZ).replace(hour=EXIT_HM[0], minute=EXIT_HM[1]))


def next_window(now: pd.Timestamp, events: list[date]) -> Window | None:
    for e in events:
        w = window_for(e)
        if now < w.exit:
            return w
    return None


def decide(now: pd.Timestamp, w: Window | None, in_trade: bool, position: int) -> str:
    """What to do right now. Pure function so the schedule logic is testable without IB."""
    if position != 0 and not in_trade:
        return "refuse"                       # someone else's MNQ position - never touch it
    if in_trade:
        if position == 0:
            return "stopped"                  # protective stop filled while we were away
        if w is None or now >= w.exit:
            return "exit"
        return "hold"
    if w is None:
        return "done"
    if now < w.entry:
        return "wait"
    if now < w.entry + pd.Timedelta(minutes=ENTRY_GRACE_MIN):
        return "enter"
    return "skip"                             # missed the 14:00 entry; don't enter late


# ---------------------------------------------------------------- state
def load_state(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def save_state(path: Path, s: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(s, indent=2, default=str))
    tmp.replace(path)


def append_trade(path: Path, rec: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(rec, default=str) + "\n")


# ---------------------------------------------------------------- IB side
class Runner:
    def __init__(self, cfg, outdir: Path = OUT, alerts=None):
        from .broker.ibkr import IBKRBroker
        from .contracts import SPECS
        from .journal import Alerts
        self.cfg, self.out = cfg, outdir
        self.alerts = alerts or Alerts()
        self.spec = SPECS[cfg.instrument.root]
        self.broker = IBKRBroker(cfg, self.spec, live_authorized=False)   # paper lock lives in here
        self.state_path = outdir / "state.json"

    # -- connection with retries (TWS restarts nightly; the GTC stop stays at IB meanwhile)
    def connect(self, tries: int = 60, wait_s: int = 60):
        for i in range(tries):
            try:
                self.broker.connect(startup_checks=False)
                return
            except (ConnectionError, OSError, TimeoutError) as e:
                log.warning("IB connect failed (%s), retry %d/%d in %ds", type(e).__name__, i + 1, tries, wait_s)
                if i == 0:
                    self.alerts.send("warning", "PAPER: can't reach TWS. Is it running and logged into Paper? "
                                                f"Retrying every {wait_s}s for {tries * wait_s // 60} min.")
                time.sleep(wait_s)
        msg = "Could not reach TWS/IB Gateway. The protective stop (GTC) is still working at IB."
        self.alerts.send("error", f"PAPER fomc-paper gave up reconnecting after {tries} tries. {msg} "
                                  "Log TWS into Paper and rerun `py cli.py fomc-paper`.")
        raise RuntimeError(msg)

    def contract(self, st):
        from ib_async import Contract
        if st.get("con_id"):
            c = Contract(conId=int(st["con_id"]), exchange=self.cfg.instrument.exchange)
            q = self.broker.ib.qualifyContracts(c)
            if q:
                return q[0]
        return self.broker.contract

    def position(self, con) -> int:
        return int(sum(p.position for p in self.broker.ib.positions() if p.contract.conId == con.conId))

    def _market(self, con, action: str, why: str) -> float:
        from ib_async import MarketOrder
        o = MarketOrder(action, 1)
        o.orderRef, o.tif = f"{REF}:{why}", "DAY"
        t = self.broker.ib.placeOrder(con, o)
        for _ in range(60):
            self.broker.ib.sleep(1)
            if t.orderStatus.status == "Filled":
                return float(t.orderStatus.avgFillPrice)
        raise RuntimeError(f"{action} market order not filled in 60 s (status {t.orderStatus.status})")

    def _place_stop(self, con, stop: float):
        from ib_async import StopOrder
        o = StopOrder("SELL", 1, stop)
        o.orderRef, o.tif = f"{REF}:stop", "GTC"   # GTC: must survive the overnight session break
        return self.broker.ib.placeOrder(con, o)

    def _our_stops(self, con):
        return [t for t in self.broker.ib.openTrades()
                if t.contract.conId == con.conId and t.order.orderType == "STP" and (t.order.orderRef or "").startswith(REF)]

    def ensure_stop(self, con, st):
        if not self._our_stops(con):
            log.warning("No working protective stop found - re-placing at %s", st["stop"])
            self._place_stop(con, st["stop"])
            self.alerts.send("warning", f"PAPER: protective stop was missing - re-placed at {st['stop']:.2f}.")
            self.broker.ib.sleep(2)

    def enter(self, w: Window, test: bool = False) -> dict:
        con = self.broker.contract
        fill = self._market(con, "BUY", "entry")
        stop = self.spec.round_to_tick(fill * (1 - STOP_FRAC))
        self._place_stop(con, stop)
        self.broker.ib.sleep(2)
        st = {"in_trade": True, "test": test, "event": str(w.event), "planned_exit": str(w.exit),
              "con_id": con.conId, "local_symbol": con.localSymbol, "entry_time": str(pd.Timestamp.now(tz=TZ)),
              "entry": fill, "stop": stop}
        save_state(self.state_path, st)
        log.warning("ENTERED long 1 %s @ %.2f, GTC stop %.2f (paper)", con.localSymbol, fill, stop)
        self.alerts.send("info", f"{'TEST ' if test else ''}PAPER ENTRY: bought 1 {con.localSymbol} @ {fill:.2f}. "
                                 f"Stop {stop:.2f} (3%) held at IB. Planned exit {ct(w.exit)}.")
        return st

    def exit(self, st, reason: str) -> None:
        con = self.contract(st)
        for t in self._our_stops(con):
            self.broker.ib.cancelOrder(t.order)
        self.broker.ib.sleep(2)
        if self.position(con) != 1:
            raise RuntimeError(f"Expected +1 {st['local_symbol']} before exit, found {self.position(con)}; not trading.")
        px = self._market(con, "SELL", "exit")
        self._record(st, px, reason)

    def _record(self, st, exit_px, reason):
        net = (exit_px - st["entry"]) * self.spec.point_value - 2 * self.cfg.instrument.commission_per_side
        rec = {"label": "FORWARD PAPER (IB paper account) - not a backtest" if not st.get("test") else "PLUMBING TEST - not a result",
               "hypothesis": "H8 pre-FOMC drift", "event": st["event"], "contract": st["local_symbol"],
               "entry_time": st["entry_time"], "entry": st["entry"], "stop": st["stop"],
               "exit_time": str(pd.Timestamp.now(tz=TZ)), "exit": exit_px, "exit_reason": reason,
               "net_usd_est": round(net, 2)}
        append_trade(self.out / ("test_trades.jsonl" if st.get("test") else "forward_trades.jsonl"), rec)
        save_state(self.state_path, {"in_trade": False, "last": rec})
        log.warning("CLOSED %s @ %.2f (%s), est. net $%.2f", st["local_symbol"], exit_px, reason, net)
        verb = "STOPPED OUT" if reason.startswith("stop") else "EXIT"
        self.alerts.send("warning" if verb == "STOPPED OUT" else "info",
                         f"{'TEST ' if st.get('test') else ''}PAPER {verb}: sold 1 {st['local_symbol']} @ {exit_px:.2f} "
                         f"(entry {st['entry']:.2f}, {reason}). Est. net ${net:+,.2f}. Simulated, not real money.")

    def stopped_out(self, st) -> None:
        con = self.contract(st)
        px = None
        for f in self.broker.ib.fills():
            if f.contract.conId == con.conId and f.execution.side == "SLD" and (f.execution.orderRef or "").startswith(REF):
                px = float(f.execution.price)
        self._record(st, px if px is not None else st["stop"], "stop" + ("" if px is not None else " (fill price not seen; stop level used)"))


def ct(ts) -> str:
    """Timestamp as phone-friendly Central time, e.g. 'Tue 1:00 PM CT' (the user is in Kentucky)."""
    t = pd.Timestamp(ts).tz_convert("America/Chicago")
    return f"{t:%a} {t.hour % 12 or 12}:{t:%M} {'AM' if t.hour < 12 else 'PM'} CT"


def keep_awake(on: bool = True) -> None:
    """On Windows, stop the PC from sleeping while a trade is being tracked (no effect elsewhere)."""
    try:
        import ctypes
        ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001
        kernel32 = ctypes.windll.kernel32           # type: ignore[attr-defined]  # Windows only
        kernel32.SetThreadExecutionState(ES_CONTINUOUS | (ES_SYSTEM_REQUIRED if on else 0))
    except (AttributeError, OSError):
        pass


def due_today(now: pd.Timestamp, events: list[date], in_trade: bool) -> bool:
    """Should the daily scheduled task start the tracker now? Yes if a trade is open (resume it) or if
    today is an entry day and the 14:00 ET entry hasn't passed yet. Pure function, unit-tested."""
    if in_trade:
        return True
    w = next_window(now, events)
    return w is not None and w.entry.date() == now.date() and now < w.entry + pd.Timedelta(minutes=ENTRY_GRACE_MIN)


def run(cfg, test_now: bool = False, events_path: str = "config/events.csv") -> None:
    keep_awake(True)
    r = Runner(cfg)
    r.connect()
    try:
        _loop(r, test_now, events_path)
    except SystemExit as e:
        if e.code not in (None, 0):
            r.alerts.send("error", f"PAPER fomc-paper stopped: {e.code}")
        raise
    except Exception as e:
        r.alerts.send("error", f"PAPER fomc-paper crashed ({type(e).__name__}: {e}). Any GTC stop stays at IB. "
                               "Check logs\\fomc_paper\\task.log.")
        raise
    finally:
        keep_awake(False)
        if r.broker.ib.isConnected():
            r.broker.ib.disconnect()


def _reconnect(r: Runner, why: str) -> None:
    r.alerts.send("warning", f"PAPER: lost the IB connection ({why}). Any GTC stop stays at IB. Reconnecting...")
    r.connect()
    r.alerts.send("info", "PAPER: reconnected to IB.")


def _loop(r: Runner, test_now: bool, events_path: str) -> None:
    st = load_state(r.state_path)
    if test_now:
        if st.get("in_trade") or r.position(r.broker.contract) != 0:
            raise SystemExit("Not flat (or a tracked trade is open) - test refused.")
        now = pd.Timestamp.now(tz=TZ)
        st = r.enter(Window(now.date(), now, now), test=True)
        r.ensure_stop(r.contract(st), st)
        print(f"Test: long 1 {st['local_symbol']} @ {st['entry']}, GTC stop {st['stop']} working. Selling in 20 s...")
        r.broker.ib.sleep(20)
        r.exit(st, "test")
        print("Test round trip done - see logs/fomc_paper/test_trades.jsonl")
        return
    events = fomc_events(events_path)
    announced = False
    while True:
        if not r.broker.ib.isConnected():
            log.warning("Not connected to IB (TWS restart?). The GTC stop stays at IB. Reconnecting...")
            _reconnect(r, "TWS restart?")
        now = pd.Timestamp.now(tz=TZ)
        st = load_state(r.state_path)
        in_trade = bool(st.get("in_trade"))
        con = r.contract(st) if in_trade else r.broker.contract
        pos = r.position(con)
        w = window_for(pd.Timestamp(st["event"]).date()) if in_trade else next_window(now, events)
        action = decide(now, w, in_trade, pos)
        if action == "refuse":
            raise SystemExit(f"An MNQ position ({pos:+d}) exists that this tracker didn't open. Close it manually first.")
        if action == "done":
            print("No upcoming FOMC events in config/events.csv. Refresh the calendar.")
            return
        if w is None:          # decide() returns "done" when there is no window; be explicit about it
            raise RuntimeError(f"internal: action {action!r} with no trading window")
        if action == "skip":
            r.alerts.send("warning", f"PAPER: missed the {ct(w.entry)} entry for the {w.event} Fed statement - "
                                     "not entering late (rules say 14:00 ET).")
            print(f"Missed the {w.entry:%Y-%m-%d %H:%M} ET entry for the {w.event} statement - not entering late. "
                  "Start earlier next time.")
            return
        if action == "wait" and not announced:
            if w.entry.date() == now.date():
                r.alerts.send("info", f"PAPER: Fed trade today. Buying 1 MNQ at {ct(w.entry)}, selling {ct(w.exit)}.")
            print(f"Next: FOMC statement {w.event}. Entry {w.entry:%a %Y-%m-%d %H:%M} ET, exit {w.exit:%a %H:%M} ET. "
                  "Leave this window open and TWS (paper) logged in.")
            announced = True
        if action == "enter":
            r.enter(w)
        elif action == "hold":
            r.ensure_stop(con, st)
        elif action == "exit":
            r.exit(st, "time" if now < w.exit + pd.Timedelta(minutes=10) else "late (tracker was not running at 13:55)")
            print("Trade recorded in logs/fomc_paper/forward_trades.jsonl. Done until the next event.")
            return
        elif action == "stopped":
            r.stopped_out(st)
            print("Protective stop was hit. Recorded. Done until the next event.")
            return
        try:
            r.broker.ib.sleep(15)
        except (ConnectionError, OSError):
            log.warning("Lost the IB connection (TWS restart?). The GTC stop stays at IB. Reconnecting...")
            r.broker.ib.disconnect()
            _reconnect(r, "TWS restart?")
