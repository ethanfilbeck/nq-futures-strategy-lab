# Tooling: what is used, what was rejected, and why
Reviewed 2026-11-10. The rule: a small set of configured, verified tools beats a long list. Every tool here
either runs in `scripts/check.py` (and therefore in CI) or is listed as "not adopted" with a reason.

## Run everything
```
py -m pip install -r requirements.txt -r requirements-dev.txt     # once
py scripts\check.py                                               # before every push (CI runs the same thing)
py scripts\check.py --fast                                        # skip the online dependency audit
```
A failure in any required gate exits non-zero and prints the tool's full output. Nothing is silently ignored.

## Adopted
| Tool | Job here | Config | Status on 2026-11-10 |
|---|---|---|---|
| **pytest** | Unit, regression and mocked-integration tests (broker and data vendor are never contacted) | `pytest.ini` | 79 passed, 2 skipped (those two need licensed data that is not in the repo) |
| **ruff** | Lint, import order, likely-bug rules, the Bandit security rule set (`S`), naive-datetime rules (`DTZ`) | `pyproject.toml` | Clean. First run found 45 issues: 13 auto-fixed, 2 real fixes (below), the rest are documented style choices |
| **pip-audit** | Known vulnerabilities in dependencies (PyPI advisory database) | none | No known vulnerabilities |
| **scripts/verify_prereg.py** | Fails if any pre-registration differs from its frozen SHA-256, or has no hash | none | 7 of 7 match |
| **scripts/prepublish_check.py** | Blocks API keys, broker account IDs, emails, local paths, licensed data, trade prices in tracked files | in the script | Clean |
| **scripts/validate_data.py** | Sanity-checks a bar file before any backtest uses it (ordering, duplicates, OHLC consistency, tick grid, gaps, jumps) | flags | Run by hand on each new download (data is licensed, so CI cannot hold it) |
| **mypy** | Type checking | `pyproject.toml` | **Clean** (0 findings, 35 files). Was 117 on 2026-11-10; fixed the same day and promoted to a required gate |
| **GitHub Actions** | Runs `scripts/check.py` on Ubuntu (Python 3.10, 3.12) and Windows (3.12) on every push, pull request and weekly | `.github/workflows/ci.yml` | Added; first run happens on push |
| **Gitleaks (CI only)** | Scans the full git history for secrets on every push | `.gitleaks.toml` | Added. A manual pattern scan of the full history found only the `.env.example` placeholder |
| **Dependabot** | Weekly pull requests for outdated or vulnerable dependencies and Actions | `.github/dependabot.yml` | Added |
| **uv (lock file only)** | Generates `requirements.lock`, an exact cross-platform pin of every dependency, for reproducing results | none | `requirements.lock` added |

### Four real fixes these tools found
Two from the security rules:
1. `nq_bot/webhook.py` validated "the JSON body is an object" with `assert`, which Python removes under `-O`.
   A JSON list would then have reached code that expects a dict. Now an explicit check; test added.
2. `nq_bot/journal.py` passed `ALERT_WEBHOOK_URL` straight to `urllib`, which also opens `file://` and plain
   `http://`. Alerts now go only to `https://` URLs; anything else is ignored with a warning. Test added.

Two from type checking, both in the IB adapter's protection path:

3. A working stop order whose `auxPrice` was unset could be adopted, recording a stop level of `0.0` and leaving
   the position effectively unprotected. Such an order is now ignored and logged. Test added.
4. Resizing a stop used `self.stop_px`, which can be unset after a restart; the resize would have sent a stop
   order with no price. It now falls back to the working order's own price, and flattens if neither is known.
   Test added.

## Evaluated and not adopted
| Tool | Why not |
|---|---|
| **Black** | `ruff format` does the same job and ruff is already here. Auto-formatting was not turned on at all: it would rewrite nearly every line and bury the research history in one giant diff. |
| **Bandit** | Its rules are ruff's `S` set. Running both reports the same findings twice. |
| **detect-secrets** | Overlaps Gitleaks (history) and `prepublish_check.py` (project-specific patterns). One baseline scan was run: nothing found. |
| **pre-commit framework** | The hooks would be installed with a Windows Python path, and commits are also made from a Linux sandbox, where that path does not exist. `scripts/check.py` gives the same gate on both. Revisit if work moves to one machine. |
| **Polars** | The largest file is ~2.6 M one-minute bars; pandas loads it in seconds. A second dataframe library means two code paths to keep identical. |
| **scikit-learn** | No model in the project is fitted. Adding ML to data this small is the fastest route to overfitting. |
| **statsmodels / SciPy** | Current statistics (t-statistic, bootstrap percentile, Monte Carlo reshuffle) are a few lines of NumPy with unit tests. Worth adding only for a specific need, e.g. Newey-West errors or a deflated Sharpe ratio. |
| **Backtrader / vectorbt / Zipline / backtesting.py** | The value of this project is that one engine runs the backtest, the paper replay and the IB paper adapter, and a test proves they make identical trades. A framework would replace the audited fill model (next-bar open, stop-first, trade-through targets) with one whose assumptions are not controlled here. |
| **Jupyter** | Useful for exploring, and fine to use locally (VS Code runs notebooks). Kept out of the repo's results path on purpose: a result has to come from a script that a pre-registration names, run once. Notebooks make it too easy to re-run until it looks good. |
| **CodeQL** | GitHub's own scanner, free for public repos, turned on in repository settings rather than by a file. Recommended; needs the owner's click (see below). |

## Editor (local, optional)
VS Code with three extensions: `ms-python.python`, `charliermarsh.ruff`, `ms-toolsai.jupyter`.
`code --install-extension charliermarsh.ruff` and so on. `.vscode/` is git-ignored, so editor settings stay local.

## Market-data sources
| Source | Use here | Notes |
|---|---|---|
| **Databento `GLBX.MDP3`** (CME's own feed) | All backtests. `ohlcv-1m` for `MNQ.v.0`, `MES.v.0`, `M2K.v.0` | Pay per download with a cost estimate first (`scripts/databento_cost.py`); roughly $9-10 for 7.5 years of one symbol in this project. Licensed: never committed. Flags degraded days. Also offers trades and quotes if bid/ask work is ever needed. |
| **CME Group contract specs** | Tick size, multiplier, expiry and roll rules in `nq_bot/contracts.py` | Free and authoritative. MNQ $2/pt, MES $5/pt, M2K $5/pt with a 0.10 tick. |
| **Interactive Brokers** | Paper-account fills and real commission schedule ($0.62/side assumed, $0.61 observed) | Historical bars exist but are rate-limited and need a live data subscription; not used for research. |
| **TradingView** | Charts and the Pine port of the ORB strategy | Good for looking, not for testing: no export of full 1-minute history, and its backtester's fill assumptions differ. |
| **Yahoo `NQ=F`, TradingView `NQ1!`** | Reference only | Continuous series stitched by the vendor. Not a tradable contract and not used in any test. |

Continuous symbols (`MNQ.v.0`, `NQ1!`, `NQ=F`) are research series. Orders only ever name a real contract month
(e.g. `MNQZ6`), resolved by `nq_bot/contracts.py` and checked against the broker's answer.

## Claude connectors
| Connector | Verdict | Why |
|---|---|---|
| GitHub (repo access from Claude) | Useful, already in use through the linked PC and git | Lets Claude read CI results and open pull requests. Grant it only this repository. |
| Context7 (library documentation) | Already connected, free | Current docs for pandas, ib_async, ruff and the like. Read-only. |
| Notion, Slack, Linear, Figma, Vercel, Supabase, Sentry, Stripe, PayPal and others | Not needed | Nothing in a single-person research repo needs them, and each one is another place a credential could leak. |
| Any brokerage or order-routing connector | **Do not install** | The project's rule is paper and simulation only. |
