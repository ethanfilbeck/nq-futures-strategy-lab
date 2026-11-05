"""Load settings.yaml into a plain nested dict with attribute access."""
from __future__ import annotations

import copy
from pathlib import Path

import yaml


class Cfg(dict):
    """dict with attribute access (cfg.risk.max_daily_loss_usd)."""

    def __getattr__(self, name):
        try:
            val = self[name]
        except KeyError as e:
            raise AttributeError(name) from e
        return Cfg(val) if isinstance(val, dict) and not isinstance(val, Cfg) else val

    def __setattr__(self, name, value):
        self[name] = value


def _wrap(d):
    if isinstance(d, dict):
        return Cfg({k: _wrap(v) for k, v in d.items()})
    return d


def load_settings(path: str | Path = "config/settings.yaml") -> Cfg:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    cfg = _wrap(raw)
    validate(cfg)
    return cfg


def override(cfg: Cfg, dotted: dict) -> Cfg:
    """Return a copy with dotted-key overrides, e.g. {'strategy.reward_risk': 1.5}."""
    new = _wrap(copy.deepcopy(dict(cfg)))
    for key, val in dotted.items():
        node = new
        parts = key.split(".")
        for p in parts[:-1]:
            node = node[p]
        node[parts[-1]] = val
    return new


def validate(cfg: Cfg) -> None:
    r = cfg.risk
    problems = []
    if cfg.mode not in ("paper", "live"):
        problems.append("mode must be 'paper' or 'live'")
    if not 0 < r.max_risk_per_trade_pct <= 2:
        problems.append("max_risk_per_trade_pct must be in (0, 2]")
    if r.max_daily_loss_usd <= 0 or r.max_risk_per_trade_usd <= 0:
        problems.append("loss limits must be positive")
    if r.max_contracts < 1:
        problems.append("max_contracts must be >= 1")
    if not 0 < r.max_margin_utilization <= 1:
        problems.append("max_margin_utilization must be in (0, 1]")
    if cfg.instrument.root not in ("NQ", "MNQ"):
        problems.append("instrument.root must be NQ or MNQ")
    if problems:
        raise ValueError("Invalid settings: " + "; ".join(problems))
