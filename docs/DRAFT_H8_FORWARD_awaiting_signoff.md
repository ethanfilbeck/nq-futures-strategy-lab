# Pre-registration: the forward test of H8, and what would justify real money

**DRAFT — not yet frozen.** Filed as `DRAFT_H8_FORWARD_awaiting_signoff.md` so it stays outside the `PREREG_*.md` hash gate until signed off; on sign-off it is renamed to `PREREG_H8_FORWARD.md` and hashed. Ethan reviews and signs off, then the SHA-256 goes into `PREREG_HASH.txt`
before the Dec 8-9, 2026 event. Nothing in it may change after the first forward event is recorded.

This document exists because a good result makes it tempting to move the line. The bar is set here, now,
by the version of me and the version of Ethan who are not watching a live trade go green.

## 1. The uncomfortable arithmetic, stated first

Per-event spread is about **$330** (standard deviation, consistent across the 48-event training split and
the 11-event holdout). With 8 scheduled FOMC statements a year, that fixes how long any forward test takes:

| If the true edge is | Events for 80% power (one-sided 5%) | Years at 8/yr | Expected t at n=12 | at n=24 | at n=40 |
|---|---|---|---|---|---|
| the discovery sample, **$127/event** | 42 | **5.2** | 1.33 | 1.88 | 2.43 |
| the holdout, **$33/event** | 604 | **75** | 0.35 | 0.50 | 0.64 |

Two consequences, both accepted in advance:

- **A high bar reached quickly is not available.** Any rule demanding t >= 2.5 inside three years is a rule
  designed to fail, even if H8 is completely real. Setting one would not be rigour; it would be a
  pre-committed abandonment dressed as rigour.
- **If the holdout is closer to the truth than the training split, this is not establishable in a human
  career.** That possibility is not hypothetical: the holdout is the only clean out-of-sample test that
  exists, and it came in at t 0.34.

**Also accepted in advance:** at the discovery effect size, a fully validated H8 earns about
**$127 x 8 = $1,015 a year on one contract, before tax**. Five years of waiting to unlock about $1,000 a
year is the actual trade on offer. It is written here so that the decision at the end is made against this
number and not against the excitement of a passing statistic.

## 2. What counts as a forward event

- Every scheduled FOMC statement from **Dec 8-9, 2026** onward, traded by `py cli.py fomc-paper` on the IB
  paper account with the frozen rule: buy at 14:00 ET the prior day, sell at 13:55 ET on statement day,
  server-side GTC stop at entry x 0.97, one MNQ contract.
- **Fills are IB's simulated fills, recorded as they come back.** Slippage is measured, not assumed. This is
  the first H8 evidence that does not rest on a 1-tick fill model.
- **Skipped events are recorded as skipped and count against the sample.** PC asleep, TWS down, missed
  entry window, crash - all logged by the journal. If **more than 10%** of events in the window are skipped,
  the sample is compromised and the count restarts from the next clean event. An unattended test that quietly
  drops its bad days is not a test.
- **No manual override, ever.** No skipping an event because the setup "looks wrong," no early exit, no size
  change. One override voids the whole forward sample and the count restarts. The rule is frozen or there is
  no test.

## 3. Interim checks — these can kill H8, never promote it

| At | Abandon H8 if | Otherwise |
|---|---|---|
| **12 events** (~Dec 2027) | cumulative net <= $0 | continue; no other reading is permitted |
| **24 events** (~Dec 2029) | cumulative net <= $0, or t <= 0.5 | continue |

Asymmetric on purpose. At n=12 a real $127 edge is only expected to show t 1.33, so no interim result can
justify real money. But a cumulative loss after 12 or 24 events is strong evidence against an effect that is
supposed to be positive on average, and there is no reason to spend three more years on it.

## 4. The decision point: 40 events (~Dec 2031)

Real money is considered **only** if every one of these holds:

1. **n >= 40** clean forward events, with <= 10% skipped.
2. **t >= 2.0** (one-sided) on the forward events alone. Backtests, replications and the placebo test
   contribute nothing to this number.
3. **Net > 0 after doubling the modelled slippage** to 2 ticks per side, on the recorded fills.
4. **Profit factor >= 1.20** on the forward events.
5. **Both halves positive** - first 20 events and last 20 events.
6. **No risk-control failure** per section 5.

Falling short is not a tie. If n >= 40 and the result is positive but misses the bar, **H8 is retired as
"positive but unresolvable at 8 events a year"** and forward trading stops. It does not continue
indefinitely in the hope of eventually clearing. A strategy that needs 20 years to prove itself has, in
practice, not proved itself.

## 5. Risk-control triggers — model failure, not bad luck

These are separate from performance. They fire when the system is not behaving the way the backtest assumed,
and they halt the test for investigation before any further event:

- **Any single event loses more than $800.** Worst observed single-event losses: MES **-$345**, M2K
  **-$325**, and the 3% stop never triggered in MES's 59 events. A loss past $800 on MNQ means the stop is
  not protecting as modelled.
- **Three consecutive events hit the 3% disaster stop.** The backtests had 0 of 59 (MES) and 2 of 59 (M2K).
  Three in a row is a regime change, not variance.
- **Any event where the GTC stop was not live at the broker** for the whole hold, or where the journal and
  IB disagree on the fill.

A trigger halts the test. Resuming requires finding the cause, fixing it, and recording both here - and the
events before a fix caused by a code defect do not count toward n.

## 6. Prerequisites before a single real dollar, even if section 4 passes

Statistics are necessary, not sufficient:

- IB account converted to **margin** (currently Cash type and cannot hold overnight futures at all).
- Account funded so that **$800 - the section 5 trigger - is at most 2% of the account**, i.e. roughly
  **$40,000 or more**. Sizing a position so one bad event is a small fraction of capital is the whole point.
- **One contract. No scaling, for the first 10 real events**, whatever the paper record says.
- Every risk control verified live on the real account exactly as the 13 paper drills verified them: kill
  switch, restart-safe risk state, missing-stop repair, stale-data halt, clean flatten.
- A written answer to: *what would make me stop?* - decided before the first real trade, not during a
  losing run.

## 7. The rules cannot change after seeing results

- This document's SHA-256 goes in `PREREG_HASH.txt` and is pushed **before the Dec 8-9, 2026 event**, and
  `scripts/verify_prereg.py` checks it in CI on every commit thereafter.
- Any change to sections 2 through 6 after the first forward event is recorded **voids the forward sample**
  and the count restarts from zero. There is no amendment procedure, deliberately.
- Forward results are published to `docs/RESULTS_H8_FORWARD.md` as they accumulate, including every losing
  event and every skipped one.
- **The null result gets published too.** If H8 is abandoned at an interim check, or retired at 40 events,
  that write-up is as much a deliverable as a pass would be.
