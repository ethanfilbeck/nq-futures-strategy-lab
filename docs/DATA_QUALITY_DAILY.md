# Data-quality report: free daily NQ history

Written 2026-11-11. **No data was purchased and none was downloaded** — in fact none *could* be, which is
itself a finding (§4). This assesses what free daily history exists and whether it is fit for research, in
advance of wanting it.

## 1. Verdict

| Source | Instrument | Coverage | Roll handling | Fit for this research |
|---|---|---|---|---|
| Stooq / Yahoo `^NDX` | Nasdaq-100 **index** | **1985 →** (~41y) | **No roll exists** | **Best available.** Not a tradeable series |
| Stooq / Yahoo `NQ=F`, `nq.f` | NQ futures, continuous | ~1999/2000 → (~26y) | **Undocumented** | **Refused** — see §3 |
| Portara `ND` / `ENQ` | NQ futures, per contract | **1996-04-10 →** (~30y) | Exact, your choice of adjustment | **Paid** — out of budget |
| Databento `GLBX.MDP3` | MNQ, per contract | 2019-05 → (7.5y) | Exact, already solved | Already owned; too short (`FEASIBILITY_CALENDAR_SPREAD.md`) |

**The recommendation is the index, not the futures.** The reasoning is uncomfortable but clean: the longest
free *futures* series is the one whose defect this project has already been burned by, and the index has
twice the history with that defect structurally absent.

## 2. Why the index is acceptable despite not being tradeable

An index is not a futures contract, so an index-based result is not a backtest. It is a **screening
instrument**: it answers "does this market behaviour exist over 41 years?" before any tradeable claim is
made. What it cannot do is price a strategy, for three reasons that must be stated in any pre-registration
using it:

- **No dividends.** `^NDX` is a price index. A futures position earns neither the dividend yield (~0.7% on
  the Nasdaq-100) nor pays the financing leg; the two partly offset but do not cancel.
- **No financing.** A futures return is a *levered excess* return. Index price returns are neither.
- **No execution.** No bid-ask, no commission, no slippage. Costs must be imposed from the project's
  audited assumptions (`$0.62`/side + 1 tick) at the stage where a tradeable rule is written, not inferred
  from the index.

So the honest design is two stages: screen the behaviour on 41 years of index data, and only if it survives,
price it on the 7.5 years of MNQ contract data already owned — accepting that the second stage cannot itself
clear t ≥ 3.5 (§6) and so is a *cost* and *implementability* check, not a significance test.

## 3. Why the free continuous futures series is refused

The free continuous NQ series from Stooq and Yahoo are documented in third-party surveys as continuous
contracts whose **roll methodology is "often unclear or undocumented"** and which may or may not be
back-adjusted.

This project has already paid for that exact defect. A Databento continuous symbol splices quarterly
contracts *without* back-adjustment, so every roll prints the calendar spread as a jump of +0.64% to +1.38%.
That artifact accounted for 16% of H8's net on MNQ, **60% on MES** and 44% on M2K
(`AUDIT_2026_11_ROLLS.md`), and resolving it cost a $0.92 download of 31 individual contracts plus two days
of work.

The recovery was only possible because Databento provides a `symbol` column and a symbology API, which gave
**exact** roll dates. A free CSV from Stooq offers neither. There would be no way to detect the contamination,
no way to measure it, and no way to correct it — only `nq_bot/rolls.py`'s heuristic detector, which is
documented as missing 11 of 25 rolls in the low-carry years 2019–21 precisely when the gap hides inside
ordinary noise.

Using an undocumented-roll series after that experience would be the single clearest way to repeat a known
error. **Refused**, and recorded here so it is not re-proposed.

## 4. Neither environment can reach the data

Tested rather than assumed. From both the cloud container and the Linux bridge VM on the PC:

```
  000   https://stooq.com/q/d/l/?s=nq.f&i=d
  000   https://query1.finance.yahoo.com/v7/finance/download/%5ENDX
  200   https://pypi.org/simple/
```

Both environments are allow-listed to package registries and block financial-data hosts. **Any download has
to be run by Ethan**, in his own PowerShell, outside the bridge. That is an operational constraint on the
plan, not an obstacle to it, but it means a fetch script has to be handed over rather than executed here.

## 5. Licensing

None of these series may be committed to the repository, which is public under MIT.

- **Yahoo Finance:** terms prohibit redistribution and commercial use. Personal research only.
- **Stooq:** free download for personal use; redistribution not granted.
- **Nasdaq-100 index values:** licensed by Nasdaq. Index *levels* are not freely redistributable either.

This is already enforced and needs no new machinery: `.gitignore` excludes `data/`, and
`scripts/prepublish_check.py` scans for licensed content before publication — it currently checks 165 files
clean. The project also has a live reason to be careful: **GitHub Support ticket #4984151**, concerning
cached orphaned commits that carried licensed per-trade prices, is still open.

**Rule for this phase: raw data stays in `data/`, never in git. Only derived statistics — counts, means,
t-statistics — go into a results document.**

## 6. Known limitations of the index series

To be stated in advance in any pre-registration, because each one is a way to be fooled:

1. **Survivorship in the index itself.** The Nasdaq-100 is reconstituted annually. Its history embeds
   decades of additions and deletions, so a long-horizon result partly reflects index construction rather
   than market behaviour. This is why the research below is restricted to *calendar-timing* effects, where
   constituent changes are a second-order concern, and not to anything resembling stock selection.
2. **Regime concentration.** 1985–2026 contains 1987, the dot-com bubble and crash, 2008, COVID and the
   2022 rate shock. A 41-year t-statistic can rest on a handful of episodes, so `t_dropping_best` from
   `research_report.py` and an explicit episode-exclusion sensitivity are mandatory.
3. **Missing and holiday sessions.** Half-days and exchange holidays must be handled explicitly. The PBO
   work already found the cost of getting this wrong: the first matrix silently discarded **$322.70** of
   P&L on exchange half-days, and `pbo.daily_matrix` now raises rather than dropping observations.
4. **No volume.** Index series carry no meaningful volume, so nothing volume-conditioned can be screened.
5. **The 1985–1999 period has no NQ futures at all.** Any pre-1999 result is a statement about the index,
   and cannot be claimed as a statement about a tradeable contract.
6. **Price-return only**, as in §2.

## 7. What a fetch would have to do

Specified but **not written**, because no candidate has been approved yet and writing a fetcher first is how
a research question gets shaped by whatever the data happens to support:

- pull `^NDX` daily OHLC, 1985 → present, to `data/ndx_daily.csv` (gitignored);
- run `scripts/validate_data.py` on it, which already checks the time grid, gaps and large moves;
- assert no duplicate dates, no zero or negative prices, and that every absent date is an actual exchange
  holiday rather than a missing observation — the `zero_is_not_missing` and `no_dates_lost` checks in
  `nq_bot/integrity.py` exist for this and run before any backtest;
- record the row count, first and last date, and a SHA-256 of the file in the pre-registration, so the
  analysis is pinned to one specific download.
