# Audit: `scripts/preflight_power.py` — four defects found, all four fixed

Written 2026-11-11, the same day the gate was written. Audited by **Monte Carlo simulation**, not by
re-reading the closed form, because re-deriving an expression from itself proves nothing. 20,000 paths per
cell, seeded, daily returns, `t` computed the way a researcher actually computes it (`mean/sd * sqrt(n)` on
the realised path).

**Verdict: the first version was optimistic on three axes at once and would have approved H8's own sample.**
It is now stricter and the three missing corrections are regression-tested. One worry turned out not to
bite, and that is recorded too.

| # | Defect | Status |
|---|---|---|
| 1 | Reported the Sharpe for a **50% chance** of clearing the bar, i.e. a coin flip | **Fixed** — `--power`, default 0.8 |
| 2 | **Serial correlation ignored**; up to 21× the nominal false-positive rate | **Fixed** — `--autocorr`, Lo (2002) inflation |
| 3 | **Overlapping observations ignored**; 22–43% false-positive rate | **Fixed** — `--hold-days`, refuses and warns |
| 4 | MinBTL evaluated only at the **required** Sharpe, which flatters it | **Fixed** — also reported at the plausible Sharpe |
| — | Non-normal returns (fat tails, negative skew) | **Checked, not a defect** — see §5 |

---

## 1. The required Sharpe was a coin flip (independently verified)

`t ≈ S·√T` is correct as a *point* relationship, and simulation confirms it to two decimals. But solving it
for `S` gives the Sharpe at which the *expected* `t` equals the bar — so a true effect of exactly that size
clears the bar **half the time**:

| Sample | Gate's original "required" S | Simulated mean t | **P(t ≥ 3.5)** |
|---|---|---|---|
| 7.5 years | 1.278 | 3.50 | **50.1%** |
| 30 years | 0.639 | 3.50 | **50.1%** |

A gate whose pass mark gives a 50/50 outcome is not a power calculation. The fix adds the power term,
`S ≥ (B + z_power)/√T`, verified by bisection against simulation:

| Sample | Simulated S for 80% power | Closed form `(B + z₀.₈)/√T` |
|---|---|---|
| 7.5 years | **1.59** | 1.59 |
| 30 years | **0.79** | 0.79 |

Simulation and closed form agree exactly, so the corrected formula is now trusted. The MNQ sample's
requirement rises from 1.28 to **1.59**, which is further above the credible ceiling, not closer to it.

## 2. Serial correlation was ignored

The gate assumed independent observations. Under AR(1) returns an iid standard error understates the truth
by `√((1+ρ)/(1−ρ))`. Measured directly, under a **pure null** with no effect at all:

| AR(1) ρ | P(t ≥ 3.5 \| no effect) | vs nominal 0.023% |
|---|---|---|
| 0.00 | 0.025% | 1× (confirms the simulator) |
| 0.10 | 0.083% | 3.6× |
| 0.20 | 0.275% | **12×** |
| 0.30 | 0.483% | **21×** |

The direction matters: positive autocorrelation makes a *false* result look significant, so this defect
caused the gate to **approve** studies that were overstated. The ρ = 0.05 cell came in at 0.017%, below
nominal — at 12,000 paths the expected count in that tail is about 3, so single cells at this extreme are
noisy; the trend across ρ is the signal, not any one row.

The fix also handles ρ < 0 correctly, *lowering* the requirement, because a mean-reverting equity curve
genuinely needs less and the gate must not over-refuse it.

## 3. Overlapping observations — the serious one

Holding `h` days while rebalancing daily does not create new information, it reuses it. The gate's
`--years` mode treated `T` years as `T` years of independent information regardless. Measured under a pure
null over 30 years of daily data:

| Holding period | P(t ≥ 3.5 \| **no effect**) | Non-overlapping obs |
|---|---|---|
| 1 day | 0.000% | 7,560 |
| 5 days | **5.3%** | 1,512 |
| 21 days | **22.3%** | 360 |
| 63 days | **31.8%** | 120 |
| 252 days | **42.5%** | 30 |

**A 30-year daily study with a monthly hold clears t ≥ 3.5 on pure noise about one time in five.** The
1-day row returned zero occurrences, which at 6,000 paths has an expected count of 1.4 and so is consistent
with the nominal rate rather than evidence of anything.

This defect mattered most because it was aimed exactly where the project was heading: every obvious
daily-horizon candidate — momentum lookbacks, volatility management, seasonality — holds positions for
weeks. The gate would have waved all of them through.

The fix takes `--hold-days`, reports the non-overlapping count, and **requires** that the final `t` be
computed on non-overlapping observations or with Newey-West. It is why `--years 30 --hold-days 21
--autocorr 0.25` is now **REFUSED** where plain `--years 30` passes.

## 4. MinBTL was evaluated at a flattering Sharpe

Bailey et al. (2014) minimum backtest length is `2·ln(N)/S²`. The gate passed the *required* Sharpe as `S`,
and a high threshold is easy not to reach by luck, so MinBTL came out reassuringly short — 3.0 years
against 7.5 available. Evaluated at a *plausible* Sharpe it says the opposite. For 12 trials:

| Evaluated at | MinBTL |
|---|---|
| Required Sharpe 1.59 | 2.0 years |
| **Credible Sharpe 1.00** | **5.0 years** |

Both are now printed, with the second labelled as the honest one.

## 5. Non-normality was checked and is **not** a defect

The one worry that did not bite. Under a pure null at t ≥ 3.5:

| Return distribution | P(t ≥ 3.5 \| no effect) |
|---|---|
| Normal | 0.030% |
| Student-t(6) | 0.005% |
| Student-t(4) | 0.015% |
| Student-t(3) | 0.010% |
| Negative skew −0.5 / −1.0 / −2.0 | 0.025% / 0.050% / 0.040% |

Symmetric fat tails are **conservative** at this bar: an outlier inflates the sample standard deviation,
which deflates `t`. Moderate negative skew is roughly neutral. No correction was added, because adding one
would make the gate stricter on no evidence. This is recorded so the question is not re-opened.

## 6. Where the gate can still be wrong

Stated plainly, because a control whose limits are undocumented invites misplaced trust.

**It could incorrectly REJECT a viable study:**
- **The ceiling is a judgement, not a measurement.** `CEILING = 1.0` decides outcomes. A genuine
  short-horizon microstructure effect with Sharpe 3 over two years would be refused, and refused wrongly.
  The ceiling encodes "no single-market directional effect exceeds 1.0," which is an empirical prior about
  *this* instrument and *this* account, not a law.
- **`EFFECT_CEILING = 0.4` is likewise a judgement**, anchored on H8's measured 0.33. An event study with
  few but genuinely large observations would be refused.
- **Equivalence tests are not covered.** Deliberately *disproving* an effect is a legitimate study that this
  gate would refuse for lacking the power to confirm one.

**It could incorrectly APPROVE an underpowered study:**
- **`--autocorr` and `--hold-days` are declared, not measured.** A researcher who understates either gets a
  pass they did not earn. The gate cannot check them before the data exists, which is the price of running
  before the pre-registration rather than after.
- **The reference Sharpes are mostly GROSS**, while the requirement is net. Comparing them already favours
  proceeding, so the ceiling is more generous than it looks.
- **No familywise adjustment of the bar itself.** `--trials` reports MinBTL but does not raise the required
  Sharpe for the number of hypotheses in the family.
- **Regime shifts are invisible to it.** The calendar-spread assessment found the signal spanned about three
  rate regimes in 7.5 years, so its effective independent sample was single digits while the gate saw 7.5
  years. Nothing in the arithmetic catches that; it needs judgement, stated in the pre-registration.
- **It assumes the per-trade `t` bar and an annualised Sharpe are interchangeable.** For this project that is
  empirically supported — daily Sharpe tracks per-trade `t` at correlation 0.9997 across the twelve
  hypotheses — but it is an assumption, and it is only known to hold for that family.

## 7. The finding that matters most

Re-run against H8's own sample, the corrected gate **refuses it**: 59 events need an effect of **0.57**
standard deviations per event for 80% power at t ≥ 3.5, against a credible ceiling of 0.40 and an H8
measurement of **0.33**. It would take **118** events.

The first version passed it, against an unjustified 0.5 cut at 50% power.

That is the audit's real result. The gate's own first draft would have approved the one hypothesis this
project already knows produced a failed holdout — which is both the reason the audit was worth running and
a reasonable basis for trusting the corrected version more than the original.

## Reproducing this

The simulations are deliberately not committed as a script: they are a one-off audit, and a committed
version would invite re-running it as a test rather than re-deriving it independently. The parameters are
above in full (20,000 paths, seeds 20261111 and 7, 252 trading days, `t = mean/sd·√n`). `tests/
test_preflight_power.py` holds 18 regression tests covering every defect and both failure modes of a gate —
refusing everything, and approving everything.
