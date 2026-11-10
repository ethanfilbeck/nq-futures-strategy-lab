# Architecture
One engine, three brokers. The same code path handles a 2021 bar in a backtest and a live bar on the IB paper
account; only the broker at the end changes. A readiness script proves the paper runner and the backtester make
identical trades on real sessions.

```
bar -> features -> regime -> strategy -> event blackout -> risk gates + sizing -> broker -> journal / alerts
                                                                                   |
                                             sim.py (backtest, replay, paper-live) | ibkr.py (IB PAPER account)
```

## Layers
| Layer | Modules | Reaches a broker? |
|---|---|---|
| Market data | `data.py` (CSV loader, Databento download, synthetic bars), `scripts/validate_data.py`, `scripts/databento_cost.py` | No |
| Data storage | `data/` (git-ignored, licensed), `runs/` (summaries tracked, trade-level files ignored) | No |
| Features and regime | `features.py`, `regime.py`, `events.py`, `contracts.py` | No |
| Strategies | `strategy.py` (ORB), `momentum.py`, `family2.py`, `family3.py`, `family4.py` | No |
| Backtesting | `engine.py`, `backtest.py` (walk-forward), `broker/sim.py`, `broker/base.py` | No |
| Risk | `risk.py` | No |
| Statistics | `metrics.py` (PF, drawdown, Sharpe, Monte Carlo), bootstrap benchmarks in the family modules | No |
| Research runs | `run_*_prereg.py`, `run_*_replication.py`, `research_edge.py`, `wf_edge.py`, `docs/PREREG_*`, `docs/RESULTS_*` | No |
| Simulated paper trading | `paper.py`, `report.py`, `webhook.py`, `external.py` | No (simulated fills) |
| **Execution (paper-locked)** | `broker/ibkr.py`, `live.py`, `drill.py`, `fomc_paper.py` | **Yes: IB paper account only** |
| Logging and alerts | `journal.py` | No |
| Quality gates | `tests/`, `scripts/check.py`, `scripts/verify_prereg.py`, `scripts/prepublish_check.py`, `.github/` | No |

**Research and execution are separated by a test, not a promise.**
`tests/test_tooling.py::test_research_modules_do_not_import_execution_code` parses every research module and fails
if one imports `ib_async` or any execution module. Execution code imports `ib_async` lazily inside functions, so
the research side runs on a machine that does not even have it installed.

## Why the files were not moved into sub-packages (2026-11-10 review)
A `research/`, `execution/`, `data/` package split would look tidier. It was not done because:
- The pre-registrations and results documents name scripts and modules by their current paths. Moving them would
  break the paper trail that makes the results checkable.
- The Windows scheduled task, the README commands and the published walkthrough all call `cli.py` and the
  `run_*.py` scripts where they are.
- The separation that matters (research cannot reach a broker) is already enforced by the import test.
Revisit when a second instrument or strategy family needs its own engine.

## Known rough edges
- `paper.py` (simulated) imports two risk-state helpers from `live.py`. They touch no broker, but they belong in
  `risk.py`.
- Type hints are partial; mypy is advisory (see `TOOLING.md`).
- `date.today()` (the PC's local date) decides roll and startup dates. Correct for a PC in a US time zone; would
  need an explicit exchange time zone on a server elsewhere.
