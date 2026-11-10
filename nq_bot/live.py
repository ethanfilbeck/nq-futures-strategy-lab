"""Real-time runner against IBKR (paper by default)."""
from __future__ import annotations

import json
import logging
import os
import time
from datetime import date
from pathlib import Path

import pandas as pd

from .backtest import COLS
from .broker.ibkr import IBKRBroker
from .contracts import SPECS
from .data import _normalize
from .engine import Engine
from .events import EventCalendar
from .features import _hm, add_features
from .journal import Alerts, Journal

# These live in risk.py (they are risk state, not execution); re-exported so existing imports keep working.
from .risk import restore_risk_state, save_risk_state

log = logging.getLogger("nq_bot.live")
LIVE_ENV_TOKEN = "I_UNDERSTAND_THE_RISK"  # noqa: S105 (a confirmation phrase, not a credential)


def authorise_live(cfg, cli_flag: bool) -> bool:
    """Live needs ALL of: mode: live, --live, env NQBOT_ENABLE_LIVE, and a typed confirmation."""
    if cfg.mode != "live" or not cli_flag:
        return False
    if os.environ.get("NQBOT_ENABLE_LIVE") != LIVE_ENV_TOKEN:
        raise RuntimeError(f"Live requested but NQBOT_ENABLE_LIVE != {LIVE_ENV_TOKEN}")
    typed = input("Type 'TRADE REAL MONEY' to enable live execution: ")
    if typed.strip() != "TRADE REAL MONEY":
        raise RuntimeError("Live confirmation not given")
    return True


def run(cfg, live_flag: bool = False) -> None:
    live = authorise_live(cfg, live_flag)
    spec = SPECS[cfg.instrument.root]
    alerts = Alerts()
    broker = IBKRBroker(cfg, spec, live_authorized=live)
    broker.connect()  # refuses to start with any NQ/MNQ position or working order, any month
    equity = broker.net_liquidation()
    events = EventCalendar(cfg.events.file, cfg.session.timezone,
                           cfg.events.blackout_before_minutes, cfg.events.blackout_after_minutes)
    eng = Engine(cfg, broker, spec, Journal(cfg.journal.dir), alerts, events, starting_equity=equity)
    state_file = Path(cfg.journal.dir) / "risk_state.json"
    restore_risk_state(eng.risk, state_file, date.today())
    if eng.risk.killed_reason:
        raise RuntimeError(f"Kill switch is set ({eng.risk.killed_reason}). Review, then run "
                           f"`python cli.py reset-kill` to clear it deliberately.")
    alerts.send("info", f"Bot started ({'LIVE' if live else 'PAPER'}) equity ${equity:,.0f}")

    bars = broker.stream_bars()
    state = {"last": time.time()}
    rth_start, rth_end = _hm(cfg.session.rth_start), _hm(cfg.session.rth_end)

    def on_update(bars_, has_new_bar):
        if not has_new_bar or len(bars_) < 3:
            return
        state["last"] = time.time()
        df = pd.DataFrame([{"timestamp": b.date, "open": b.open, "high": b.high, "low": b.low,
                            "close": b.close, "volume": b.volume} for b in bars_[:-1]])  # last bar is still forming
        df = _normalize(df.set_index("timestamp"), cfg.session.timezone)
        feats = add_features(df, cfg)
        row = feats[COLS].iloc[-1].to_dict()
        try:
            eng.on_bar(feats.index[-1], row)
            save_risk_state(eng.risk, state_file)
        except Exception as e:  # any engine error: protect capital first
            log.exception("engine error")
            alerts.send("error", f"Engine error {type(e).__name__} - flattening and halting")
            eng.risk.halt_day("engine error")
            broker.flatten("engine error")

    bars.updateEvent += on_update
    try:
        while True:
            broker.ib.sleep(5)
            if not broker.is_connected():
                alerts.send("error", "Disconnected from IB. Server-side bracket orders remain. Exiting.")
                break
            now = pd.Timestamp.now(tz=cfg.session.timezone)
            m = now.hour * 60 + now.minute
            in_rth = now.weekday() < 5 and rth_start <= m < rth_end
            if in_rth and time.time() - state["last"] > cfg.session.stale_data_seconds:
                eng.risk.halt_day("stale market data")
                broker.flatten("stale data")
                alerts.send("error", "Market data stale - flattened and halted for the day")
                state["last"] = time.time()
            if broker.roll_due(date.today()) and broker.position() == 0 and not broker.has_working_entry():
                alerts.send("warning", "Contract roll date reached - exiting so a restart picks up the new month.")
                break
            if eng.risk.killed_reason:
                save_risk_state(eng.risk, state_file)
                broker.flatten(eng.risk.killed_reason)
                alerts.send("error", f"Kill switch: {eng.risk.killed_reason}. Exiting.")
                break
    except (ConnectionError, OSError) as e:
        # TWS/Gateway closed or the socket dropped: ib_async raises instead of returning, so handle it
        # here. Nothing can be sent to IB now; the bracket orders already at IB stay working.
        alerts.send("error", f"Disconnected from IB ({type(e).__name__}). Server-side bracket orders remain. Exiting.")
    except KeyboardInterrupt:
        alerts.send("warning", "Stopped by user - flattening (wait for it to finish; don't press Ctrl+C again)")
        for attempt in range(2):
            try:
                broker.flatten("user stop")
                broker.ib.sleep(2)
                break
            except KeyboardInterrupt:
                log.warning("Second Ctrl+C ignored - finishing the flatten first")
    finally:
        save_risk_state(eng.risk, state_file)
        if broker.is_connected():
            broker.ib.disconnect()


def reset_kill(path: Path) -> bool:
    if not path.exists():
        return False
    s = json.loads(path.read_text())
    if not s.get("killed_reason"):
        return False
    s["killed_reason"] = None
    s["peak_equity"] = 0.0  # drawdown is measured from the equity at next start
    path.write_text(json.dumps(s, indent=2))
    return True
