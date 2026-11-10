"""Unattended PAPER trading runner.

Completed 1-minute bars (live from Databento, or replayed from history) -> same features, regime,
strategy, risk engine and simulated broker as the backtests -> journal, persisted risk state and a
daily report. There is no code path to a real-money broker in this module.

Safeguards on every bar: stale/disconnected feed, out-of-order or duplicate bars, missing stop on an
open position, unexpected position, order quantity outside limits, abnormal bars, daily loss and
drawdown limits (via the risk engine), flat by 15:55 ET.
"""
from __future__ import annotations

import logging
import threading
import time
from pathlib import Path

import pandas as pd

from .backtest import COLS
from .broker.sim import SimBroker
from .contracts import SPECS
from .engine import Engine
from .events import EventCalendar
from .features import _hm, add_features
from .journal import Alerts, Journal
from .live import restore_risk_state, save_risk_state
from .report import write_daily_report

log = logging.getLogger("nq_bot.paper")
KEEP_DAYS = 35


class PaperRunner:
    def __init__(self, cfg, history: pd.DataFrame | None, outdir: str | Path = "logs/paper",
                 alerts: Alerts | None = None, persist: bool = True, clock=time.time):
        self.cfg = cfg
        self.spec = SPECS[cfg.instrument.root]
        self.out = Path(outdir); self.out.mkdir(parents=True, exist_ok=True)
        self.alerts = alerts or Alerts()
        self.journal = Journal(self.out)
        self.broker = SimBroker(self.spec, cfg.instrument.slippage_ticks)
        events = EventCalendar(cfg.events.file, cfg.session.timezone,
                               cfg.events.blackout_before_minutes, cfg.events.blackout_after_minutes)
        self.engine = Engine(cfg, self.broker, self.spec, self.journal, self.alerts, events)
        self.state_file = self.out / "risk_state.json"
        self.persist = persist
        if persist:
            restore_risk_state(self.engine.risk, self.state_file, pd.Timestamp.now(tz=cfg.session.timezone).date())
        self.hist = history.copy() if history is not None and len(history) else \
            pd.DataFrame(columns=["open", "high", "low", "close", "volume"], dtype=float)
        self.lock = threading.Lock()
        self.clock = clock
        self.last_bar_wall = clock()
        self.last_ts = self.hist.index[-1] if len(self.hist) else None
        self.bars_today = 0
        self.gaps_today = 0
        self.rth_bars_today = 0
        self.day = None
        self.extra = []
        self._setup_strategy_features()
        self.journal.write(pd.Timestamp.now(tz="UTC"), "paper_start", strategy=cfg.strategy.name,
                           history_bars=len(self.hist))
        self.alerts.send("info", f"Paper runner started (strategy: {cfg.strategy.name}, SIMULATED orders only)")

    def _setup_strategy_features(self):
        name = self.cfg.strategy.name
        if name == "intraday_momentum":
            from .momentum import MOM_COLS, add_momentum_features
            self.extra = [(add_momentum_features, MOM_COLS)]
        elif name in ("sweep", "vwap_pullback"):
            from .family2 import F2_COLS, add_family2_features
            self.extra = [(add_family2_features, F2_COLS)]

    # ------------------------------------------------------------------ bars
    def on_bar(self, ts: pd.Timestamp, o: float, h: float, l: float, c: float, v: float) -> None:
        with self.lock:
            ts = ts.tz_convert(self.cfg.session.timezone)
            if self.last_ts is not None and ts <= self.last_ts:
                self.journal.write(ts, "data_issue", issue="duplicate or out-of-order bar ignored")
                return
            if not (l <= min(o, c) and h >= max(o, c)) or min(o, h, l, c) <= 0:
                self.journal.write(ts, "data_issue", issue="malformed bar ignored", bar=[o, h, l, c])
                return
            rth_s, rth_e = _hm(self.cfg.session.rth_start), _hm(self.cfg.session.rth_end)
            m_now = ts.hour * 60 + ts.minute
            if self.last_ts is not None and ts.date() == self.last_ts.date() and rth_s < m_now < rth_e:
                m_prev = self.last_ts.hour * 60 + self.last_ts.minute
                if m_prev >= rth_s and (ts - self.last_ts).total_seconds() / 60 - 1 >= 1:
                    self.gaps_today += 1  # missing minute(s) inside regular hours
            self._roll_day(ts)
            self.last_ts = ts
            self.last_bar_wall = self.clock()
            self.bars_today += 1
            if rth_s <= m_now < rth_e:
                self.rth_bars_today += 1
            self.hist.loc[ts] = [o, h, l, c, v]
            cutoff = ts - pd.Timedelta(days=KEEP_DAYS)
            if self.hist.index[0] < cutoff:
                self.hist = self.hist[self.hist.index >= cutoff]

            self.broker.process_bar(ts, o, h, l, c)          # fills for orders sent on the previous bar
            feats = add_features(self.hist.iloc[-30000:], self.cfg)
            cols = list(COLS)
            for fn, extra_cols in self.extra:
                feats = fn(feats, self.cfg)
                cols += extra_cols
            row = feats[cols].iloc[-1].to_dict()
            row["_ts"] = ts
            self.engine.on_bar(ts, row)
            self._check_invariants(ts, row)
            if self.persist:
                save_risk_state(self.engine.risk, self.state_file)

    def _check_invariants(self, ts, row) -> None:
        pos = self.broker.position()
        if pos != 0 and self.broker.stop is None:
            self._emergency(ts, "open position without a protective stop", row["close"])
        elif abs(pos) > self.cfg.risk.max_contracts:
            self._emergency(ts, f"position size {pos} exceeds max_contracts", row["close"])

    def _roll_day(self, ts) -> None:
        if self.day is not None and ts.date() != self.day:
            self.end_of_day(self.day)
        if self.day != ts.date():
            self.day = ts.date()
            self.bars_today = 0
            self.rth_bars_today = 0
            self.gaps_today = 0

    # ------------------------------------------------------------------ safety
    def _emergency(self, ts, reason: str, price: float | None = None) -> None:
        """Halt new entries for the day and close any simulated position immediately."""
        self.engine.risk.halt_day(reason)
        if self.broker.position() != 0 or self.broker.has_working_entry():
            px = price if price is not None else (self.hist["close"].iloc[-1] if len(self.hist) else None)
            self.broker.flatten_now(px, ts)
            self.engine.pending = None
            self.engine.sync_broker(ts)
        self.journal.write(ts, "emergency", reason=reason)
        self.alerts.send("error", f"EMERGENCY: {reason} - flattened (simulated) and halted for the day")

    @property
    def external(self):
        """The TradingView signal queue (strategy 'tradingview' only)."""
        from .external import ExternalSignals
        if not isinstance(self.engine.strategy, ExternalSignals):
            raise RuntimeError("webhook signals need strategy 'tradingview'")
        return self.engine.strategy

    def external_flatten(self, reason: str) -> None:
        with self.lock:
            if self.last_ts is not None:
                self.engine._flatten(self.last_ts, reason)  # fills on the next bar, like every market order

    def heartbeat(self) -> None:
        """Call every few seconds from a timer: detects a stalled feed and the KILL file."""
        kill_file = self.out / "KILL"
        if kill_file.exists() and not self.engine.risk.killed_reason:
            self.kill("KILL file found (emergency stop)")
            return
        with self.lock:
            now = pd.Timestamp.now(tz=self.cfg.session.timezone)
            m = now.hour * 60 + now.minute
            in_rth = now.weekday() < 5 and _hm(self.cfg.session.rth_start) <= m < _hm(self.cfg.session.rth_end)
            silent = self.clock() - self.last_bar_wall
            if in_rth and silent > self.cfg.session.stale_data_seconds and not self.engine.risk.day.halted_reason:
                self._emergency(now, f"no market data for {int(silent)}s (feed stale or disconnected)")

    def kill(self, reason: str = "manual kill") -> None:
        with self.lock:
            self.engine.risk.kill(reason)
            self._emergency(pd.Timestamp.now(tz=self.cfg.session.timezone), reason)
            if self.persist:
                save_risk_state(self.engine.risk, self.state_file)

    def end_of_day(self, day) -> Path | None:
        if self.rth_bars_today == 0:
            return None  # Sunday evening / holiday: no regular session, no report
        path = write_daily_report(self.out, day, self.engine.trades, self.journal.path,
                                  bars=self.bars_today, gaps=self.gaps_today,
                                  halted=self.engine.risk.day.halted_reason, killed=self.engine.risk.killed_reason,
                                  strategy=self.cfg.strategy.name, equity=self.engine.risk.equity)
        self.alerts.send("info", f"Daily report written: {path.name}")
        return path


# ====================================================================== feeds
def replay(runner: PaperRunner, bars: pd.DataFrame) -> None:
    """Feed historical bars one at a time through the runner, exactly as live bars would arrive."""
    for ts, r in bars.iterrows():
        runner.on_bar(ts, r["open"], r["high"], r["low"], r["close"], r["volume"])
    if runner.day is not None:
        runner.end_of_day(runner.day)


def databento_history(key: str, symbol: str, days: int = KEEP_DAYS) -> pd.DataFrame:
    """Recent 1-minute bars for warm-up (indicators need ~20 sessions). Small, cheap request."""
    import databento as db

    from .data import _normalize
    client = db.Historical(key)
    rng = client.metadata.get_dataset_range(dataset="GLBX.MDP3")
    end = pd.Timestamp(rng["end"] if isinstance(rng, dict) else rng.end)
    start = end - pd.Timedelta(days=days)
    data = client.timeseries.get_range(dataset="GLBX.MDP3", schema="ohlcv-1m", symbols=[symbol],
                                       stype_in="raw_symbol", start=start, end=end)
    df = data.to_df()
    return _normalize(df[["open", "high", "low", "close", "volume"]])


def run_databento_live(runner: PaperRunner, key: str, symbol: str, start=None) -> None:
    """Stream live 1-minute bars for `symbol` (e.g. MNQZ6) into the runner until stopped."""
    import databento as db
    stop = threading.Event()

    def beat():
        while not stop.is_set():
            runner.heartbeat()
            stop.wait(5)

    threading.Thread(target=beat, daemon=True).start()
    client = db.Live(key=key)
    client.subscribe(dataset="GLBX.MDP3", schema="ohlcv-1m", symbols=[symbol], stype_in="raw_symbol",
                     start=start)
    try:
        for rec in client:
            if isinstance(rec, db.OHLCVMsg):
                ts = pd.Timestamp(rec.ts_event, unit="ns", tz="UTC")
                runner.on_bar(ts, rec.open / 1e9, rec.high / 1e9, rec.low / 1e9, rec.close / 1e9, float(rec.volume))
            elif isinstance(rec, db.ErrorMsg):
                runner.alerts.send("error", f"Databento error: {rec.err}")
    finally:
        stop.set()
        runner.alerts.send("error", "Live data stream ended - simulated position flattened, entries halted")
        runner._emergency(pd.Timestamp.now(tz=runner.cfg.session.timezone), "live data stream ended")
        if runner.day is not None:
            runner.end_of_day(runner.day)
