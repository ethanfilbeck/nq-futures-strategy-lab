# Quantitative research literature review

Written 2026-11-11. Purpose: stop reinventing ideas the literature has already settled, and check this
project's *method* against published standards rather than checking more strategies.

## How to read this, and what was verified

Every citation below was retrieved and checked on 2026-11-11; none is quoted from memory. Where a source is
paywalled and only its abstract and metadata could be read, **this document says so and limits its claims
accordingly.** Nothing here claims any published study shows a strategy will work on NQ or MNQ. The papers
are about *methodology*; applying their methods to this project is the point, and the applications below are
computed from this repository's own numbers.

---

# 1. Research sources and publication information

| # | Citation | Access |
|---|---|---|
| **P1** | Bailey, D. H., Borwein, J. M., López de Prado, M., & Zhu, Q. J. (2017). "The probability of backtest overfitting." *Journal of Computational Finance*, **20**(4), 39–69. DOI 10.21314/JCF.2016.322. First published online 2016-09-19. | abstract + publisher record read; full text paywalled |
| **P2** | Bailey, D. H., Borwein, J. M., López de Prado, M., & Zhu, Q. J. (2014). "Pseudo-Mathematics and Financial Charlatanism: The Effects of Backtest Overfitting on Out-of-Sample Performance." *Notices of the American Mathematical Society*, **61**(5), from p. 458. | **full preprint read** at carmamaths.org |
| **P3** | Aparicio, D., & López de Prado, M. (2018). "How hard is it to pick the right model? MCS and backtest overfitting." *Algorithmic Finance*, **7**(1–2), 53–61. DOI 10.3233/AF-180231. | abstract + publisher record only; full text paywalled |
| **D1** | CME Group, "Market by Order (MBO)" FAQ and education pages; CME MDP 3.0 Market by Order book-management documentation. | read |
| **D2** | Databento, "CME Globex MDP 3.0" dataset documentation (`GLBX.MDP3`). | read |

The end page of P2 could not be confirmed from a source that prints it, so only the start page is given.

---

# 2. Important findings

## P2 — Pseudo-Mathematics and Financial Charlatanism (the most directly useful)

**Plain language.** If you try enough strategies on the same data, one of them will look excellent purely by
chance. The paper quantifies exactly how good "by chance" looks, and therefore how much data you need before
a good-looking backtest means anything.

**The central result (their Proposition 2.1).** For N independent trials whose *true* Sharpe ratio is zero,
the expected maximum in-sample Sharpe ratio is approximately

> (1 − γ)·Z⁻¹(1 − 1/N) + γ·Z⁻¹(1 − 1/(N·e⁻¹))

where γ is the Euler–Mascheroni constant and Z⁻¹ is the inverse standard-normal CDF. The paper's worked
example: **with only N = 10 configurations, the expected maximum in-sample Sharpe is about 1.57, while the
expected out-of-sample Sharpe is zero.**

**Minimum Backtest Length (their Theorem 3.1).** Rearranged, that gives the shortest backtest for which a
given in-sample Sharpe is not simply the best of N coin flips:

> MinBTL ≈ [((1 − γ)Z⁻¹(1 − 1/N) + γZ⁻¹(1 − 1/(N·e⁻¹))) / E[max_N]]² **< 2·ln[N] / E[max_N]²**, in years

**Limitations, as the authors state them.** MinBTL is *necessary, not sufficient* — a backtest longer than
MinBTL can still be overfit. The framework does not measure overfitting, only bounds it. It assumes
independent trials (the authors call this conservative and suggest reducing the effective N for correlated
trials, e.g. by PCA) and IID normal returns for the trial-count result. Many published backtests never
report N at all, so their overfitting risk cannot be assessed.

## P1 — The Probability of Backtest Overfitting

**Plain language.** A follow-up that measures what P2 only bounds. It defines the **probability of backtest
overfitting (PBO)**: across many train/test splits, how often does the configuration that looked best
in-sample perform below median out-of-sample? A high PBO means your selection procedure is choosing noise.

**Method: Combinatorially Symmetric Cross-Validation (CSCV).** Model-free and non-parametric. Take a T×N
matrix of returns (T periods, N configurations), cut it into S blocks, form every balanced split into
train and test halves, and in each split record the out-of-sample rank of the in-sample winner. PBO is the
share of splits where that winner lands in the bottom half.

**Stated contribution.** The authors argue that standard safeguards — hold-out samples in particular — are
*unreliable* in this setting, which is why they propose PBO rather than relying on a hold-out alone.

**Limitation.** The full text is paywalled, so this summary rests on the abstract and publisher record, and
on the method as described in P2's companion discussion. No numerical result from P1 is quoted here.

## P3 — How hard is it to pick the right model?

**Plain language.** Even dedicated model-selection machinery struggles to identify the better of several
strategies from realistic amounts of financial data.

**What the record states.** The authors test the **Model Confidence Set** (Hansen et al., 2011) on a simple
machine-learning trading problem and report that MCS **"is not robust to multiple testing"** and **requires a
very high signal-to-noise ratio to be usable.** Their simulated Sharpe ratios are described as ones "rarely
seen in practice"; the paper's own footnotes cite the S&P 500 at roughly 0.38 Sharpe for 1996–2014 and note
hedge funds typically average below 2.

**Limitations, as stated.** Not robust to multiple testing; needs very high signal-to-noise; assumes a
simplified data-generating process; assumes M *independent* strategies where real ones are correlated; results
for one statistic are described as "somewhat inconsistent," with a corrigendum advising against its
elimination rule.

**Honest scope note.** Only the abstract and publisher metadata were accessible. **No specific sample size
from P3 is quoted in this document, because none could be read.** My earlier framing of this paper as being
about "how many observations are needed" is not supported by what I was able to verify.

## D1/D2 — CME order-book documentation

- **Market by Price (MBP)** is price-aggregated: top 10 levels, total quantity and order count per level.
  Queue position and individual order sizes **cannot** be determined.
- **Market by Order (MBO)** is order-level: individual orders at **all** price levels, each with an anonymous
  OrderID persisting for the order's life, so queue position and individual order sizes are visible. CME
  states MBO is supported for all Globex futures and options.
- **Databento `GLBX.MDP3`** offers MBO, MBP-10, MBP-1, trades, and aggregated schemas. Coverage runs from
  **June 2010**, but data before **2017-05-21** comes from the older MDP 2 feed, which has **no MBO**.

---

# 3. Relevant mathematical and statistical concepts

| Concept | What it is | Where it bites here |
|---|---|---|
| Expected maximum of N draws | The best of N null results is systematically positive, growing roughly with √(2·ln N) | 12 hypotheses were tested on one dataset |
| Familywise error rate | P(at least one false positive across all N tests) | Exactly the risk the rising t-bar was guarding against |
| Minimum Backtest Length | Shortest sample for which a given in-sample Sharpe is not just the best of N trials | Fixes whether 6.15 years was enough |
| PBO / CSCV | Share of train-test splits where the in-sample winner is below-median out-of-sample | Directly computable on this repo's strategies |
| Deflated / haircut Sharpe | Performance discounted for the number of trials | What a corrected H8 figure should be reported as |
| Effective number of trials | Correlated trials count for less than N | MES/M2K/MNQ are 0.85–0.95 correlated, so effective N < 12 |

---

# 4. Comparison against the experiments already run

This is where the literature meets this repository. **All figures below are computed from this project's own
results**, using the null model P2 describes (independent trials, t-statistics approximately standard normal).

## 4a. Was the rising significance bar well-calibrated? Yes — and that is a real finding

The project raised its bar informally: **t ≥ 2.5 → 3.0 → 3.5** as more hypotheses were tested, citing Harvey,
Liu & Zhu. The formal thresholds for 12 trials are:

| Familywise error rate | Required t |
|---|---|
| 5% | **2.63** |
| 1% | **3.14** |

Families 3 and 4 used t ≥ 3.0 and t ≥ 3.5 — **between the 5% and 1% thresholds, and stricter than the 5% one.**
The informal rule was not merely defensible; it was close to correctly calibrated. This is the single most
reassuring result in this review.

## 4b. Was the sample long enough? Yes, but not by much

Applying P2's MinBTL with N = 12:

- Expected maximum in-sample annualised Sharpe across 12 **pure-noise** trials: **≈ 1.02**
- **MinBTL < 2·ln(12) / 1² ≈ 4.97 years**
- Training sample actually used: 2019-05-06 → 2025-06-30 = **6.15 years**

So the backtest exceeded the minimum length, by about 24%. P2 is explicit that this is *necessary, not
sufficient*.

## 4c. Where H8 now stands against the multiple-testing null — the uncomfortable part

P(at least one of 12 independent null trials exceeds t):

| t | P(max of 12 exceeds it) | Single-trial p |
|---|---|---|
| 2.00 | 24.1% | 2.3% |
| 2.47 | 7.8% | 0.68% |
| **2.63** | **5.0%** | 0.43% |
| 2.89 | 2.3% | 0.19% |
| **3.02** | **1.5%** | 0.13% |
| 3.50 | 0.28% | 0.02% |

Against this project's actual H8 figures:

| H8 figure | t | P(best of 12 null trials beats it) | Reading |
|---|---|---|---|
| MNQ training, **as originally published** | 3.02 | **1.5%** | unlikely from noise alone |
| MNQ training, **roll-adjusted** (train-only detector) | 2.63 | **5.0%** | **exactly at the 5% familywise threshold** |
| MNQ training, **roll-adjusted** (train+holdout detector) | 2.47 | **7.8%** | below the 5% threshold |
| MNQ holdout, roll-adjusted | 0.25 | — | indistinguishable from zero |

**This is the finding that matters.** Before the roll audit, H8's t of 3.02 was comfortably past what 12
noise trials would produce. After it, H8 sits *on or just under* the 5% familywise line. The audit did not
merely shrink the effect — it moved H8 from "unlikely to be luck" to "about as likely as luck."

Two honest adjustments, pulling in opposite directions:

- **In H8's favour:** the 12 trials are *not* independent. Several share the same data and periods, so the
  effective N is below 12, which makes the true thresholds slightly lower than the table above. P2 explicitly
  notes dependent trials should be reduced to an effective count.
- **Against H8:** the 12 figure counts only *formally pre-registered* hypotheses. It excludes the ORB
  walk-forward's 8-combination parameter grid and every informal look at this data. P2's point is that the
  relevant N is the number of trials *actually performed*, which is almost always larger than the number
  reported.

## 4d. Which ideas has this project already tested?

| Literature direction | Already tested here? |
|---|---|
| Multiple-testing correction on strategy search | **Yes** — the rising bar, and section 4a shows it was close to right |
| Hold-out validation | **Yes** — MNQ holdout, used once. P1's claim that hold-outs alone are unreliable is *consistent with* what happened: H8 passed training and failed holdout |
| Placebo / sham-date controls | **Yes** — `RESULTS_H8_PLACEBO.md`. Not a technique from these three papers, but complementary to them |
| Negative controls | **Yes** — the gold control |
| PBO / CSCV | **No — never computed.** This is the clearest gap |
| Deflated Sharpe / haircutting | **No** — results are reported raw, not discounted for 12 trials |
| MCS model selection | **No**, and P3 argues against relying on it |
| Order-book microstructure | **No** — H4 tested a price-shaped *proxy* using OHLCV, which has no order-flow content at all |

---

# 5. Research gaps in this project

1. **PBO has never been computed.** It is the one method in these papers that this project could run on data
   already owned, and it directly measures whether the selection procedure picks noise. The 12 strategies have
   different trade counts and different event dates, but each can be expressed as a daily P&L series over the
   1,588 common sessions, giving the T×N matrix CSCV needs. **This is a real gap and it is free to close.**
2. **Results are reported raw.** Every result doc quotes an unadjusted t. None reports a trial-count-adjusted
   figure, which is what section 4c shows actually changes the interpretation.
3. **The number of trials is understated.** `RESEARCH_BUDGET.md` counts 12 pre-registered hypotheses. The true
   N for multiple-testing purposes includes the ORB parameter grid and any informal exploration. P2's central
   practical complaint is precisely that N goes unreported.
4. **Hold-out reliance.** P1 argues a single hold-out is not a sufficient safeguard. This project leaned on
   exactly that for H8 — and, to its credit, the hold-out did fail, which is the behaviour the paper predicts
   is possible but not guaranteed.
5. **No microstructure data at all.** Section 6.
6. **A data-layer defect none of this literature would have caught.** The November 2026 roll audit found
   contaminated prices. PBO, MinBTL and MCS all assume the return series is *correct*. None of them tests
   that. Worth stating plainly: the literature protects against over-searching, not against bad data.

---

# 6. Additional data requirements

| Need | Why | Source | Cost |
|---|---|---|---|
| Exact contract roll dates | Close out the roll audit properly | Databento `symbology.resolve` | **free** (metadata) |
| Per-contract bars over hold windows | Price each event on the contract actually held | `GLBX.MDP3`, raw symbols | cents |
| **MBO order-level data** | The only way to test queue position, order-flow imbalance or stop-clustering. MBP-10 gives aggregated depth **but not queue position or individual order sizes**, so it cannot test the H4 idea properly either | `GLBX.MDP3` MBO | **unknown — must be measured, not guessed** |
| Daily settles, front + second contract | Carry / roll-yield research direction | `GLBX.MDP3` `ohlcv-1d` | ~$1–3/market |

**On MBO cost: do not take a number from me.** I have no verified figure, and inventing one would break this
document's own rule. `metadata.get_cost` is free, so measure it:

```
py scripts\databento_cost.py --help      # then the same call with schema mbo for a single month
```

Two hard constraints from D2 that bound any microstructure plan: **MBO exists only from 2017-05-21** (earlier
data is MDP 2, which has no MBO), and order-level data is orders of magnitude larger than 1-minute bars, so
both storage and compute need checking before any purchase.

---

# 7. Recommendations for educational simulation experiments

All simulation and research only. No execution, no brokerage connection, no real money. None of these spends
a `RESEARCH_BUDGET.md` hypothesis line, because none of them is a trading hypothesis — they are tests *of the
method*.

**E1. Compute PBO for the 12 strategies already run (free, highest value).**
Build the 1,588 × 12 daily P&L matrix, run CSCV, report PBO. **Pre-register the interpretation first**: what
PBO value would mean the selection procedure is sound, and what would mean it is picking noise. Expected
learning: a direct measurement of whether this project's own search was overfitting, using the method P1
exists to provide.

**E2. Reproduce P2's Proposition 2.1 by simulation (free, one afternoon).**
Simulate N independent null strategies over T periods, record the maximum in-sample Sharpe, and compare to the
formula. Vary N from 2 to 1,000. Expected learning: a first-hand feel for how fast the best-of-N null result
grows — the single most useful intuition in this literature.

**E3. Report a trial-count-adjusted figure alongside every raw t (free).**
Add the familywise p-value from section 4c to `nq_bot/research_report.py` as a standard field, so every future
result states its raw t *and* the probability that the best of N null trials would beat it.

**E4. Count the true N honestly (free).**
Audit the repository's history for every configuration ever evaluated, including the ORB grid, and record the
real trial count in `RESEARCH_BUDGET.md`. Expect the number to exceed 12. P2's complaint is that nobody does
this; doing it is cheap and improves every threshold in section 4.

**E5. Price MBO for one instrument-month before considering any microstructure work (free to price).**
Measure the cost and the data volume. Then decide. Do not design a microstructure experiment before knowing
whether its data is affordable — that mistake already cost $6.25 on the Nikkei download.

---

## What this review does not claim

- No published study here shows that any strategy will work on NQ or MNQ. These papers are about research
  method, and P2 and P3 are specifically about how easily method goes wrong.
- No result, sample size or figure is attributed to P1 or P3 beyond what their abstracts and publisher records
  state, because their full texts are paywalled and were not read.
- The calculations in section 4 use the independent-trials null those papers describe. Real trials here are
  correlated, so the thresholds are approximations — stated as such, in both directions, in section 4c.
- Nothing here changes any strategy rule, any pre-registration, or any frozen result.
