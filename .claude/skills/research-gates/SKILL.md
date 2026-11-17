---
name: research-gates
description: Run the full pre-registration gauntlet before any new hypothesis is written or any data is bought. Use when proposing, pre-registering, or about to test a trading hypothesis in this repo, or when asked whether an idea is worth testing.
---

# Pre-registration gauntlet

Run these **in order**. Each one has refused real work; none is ceremonial. Stop at the first refusal.

## 1. Power — can the sample reach the bar at all?

```
py scripts\preflight_power.py --years <Y> --bar 3.5 --hold-days <H> --autocorr <RHO> --trials <N>
py scripts\preflight_power.py --observations <N> --bar 3.5
```

Runs **before the pre-registration is written**, not after a null result. A null from an underpowered test is
evidence of nothing, and a budget line is an expensive way to buy one.

Declare `--hold-days` honestly. A 21-day hold rebalanced daily clears t ≥ 3.5 on **pure noise 22.3% of the
time**; at 252 days it is 42.5%. Compute the final t on non-overlapping observations or with Newey-West.

On the 7.5-year MNQ sample at t ≥ 3.5 this gate **refuses everything** (it needs net Sharpe 1.59). That is
expected and correct. See `docs/POWER_GATE_AUDIT.md`, including §6 on where the gate can still be wrong.

## 2. Refutation search — attack the idea you like

Mandatory, and it exists because it was skipped once. Rebuttals were found for two candidates being
*discarded* and not searched for on the one being advanced; the refuting paper existed, was published by the
Federal Reserve, and was co-authored by an original author (`docs/FOMC_CYCLE_LITERATURE_AUDIT.md`).

- Search for **later work by the original authors** first.
- Separate the original sample from genuinely post-publication data.
- Confirm any headline Sharpe or effect size belongs to **the subset actually proposed**, not a broader
  strategy containing it.
- Confirm the holdout still exists. A window whose answer has since been published is not a holdout.
- **Record the search terms even when nothing is found.** An absence of rebuttals counts only if someone looked.

## 3. Coverage — only if new paid data is involved

```
py scripts\preflight_coverage.py <SYMBOL> <START> <END>
```

Free `metadata.get_record_count` calls. "The market is open" and "the market trades every minute" are
different claims. NKD was bought for $6.25 and came back invalid on coverage: 16 of 59 events against a floor
of 50. State bars/day and the minimum event count in the pre-registration, and report **no verdict below it**.

## 4. Write and freeze

Name it `PREREG_*.md` so `scripts/verify_prereg.py` picks it up; keep unsigned drafts named `DRAFT_*` so they
stay outside the hash gate. State in advance: the bar, the exclusion rules, what would make it fail, and the
expected effect size — then check that expectation against step 1's requirement.

## 5. Quality gates

```
py scripts\check.py
```

Six gates: ruff, pytest, pre-registration hashes, pre-publish secret/licence scan, pip-audit, mypy. All must
pass. Never silently ignore a failure — the last mypy failure was masking real type errors behind a scratch
folder being type-checked.

## Rules that do not bend

- The bar is **t ≥ 3.5** and it does not fall. Widening a ceiling is the bar by another name.
- Re-testing a rejected hypothesis in any re-parameterised form is **prohibited**, and costs no budget line
  because it is not permitted at all.
- Simulated and historical only. No live brokerage execution, no real money.
