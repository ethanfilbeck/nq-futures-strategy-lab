# Research report: daily-horizon phase

Written 2026-11-11. **No trading rules were written, no data was purchased, no budget line was spent, and
no holdout was touched.** This is the feasibility review that has to come first.

> ## RETRACTED, 2026-11-11 (same day)
>
> **The surviving candidate in this report is REJECTED.** See `FOMC_CYCLE_LITERATURE_AUDIT.md`.
>
> Knox & Vissing-Jorgensen (FEDS 2026-023) - by one of the original authors - find no systematically higher
> even-week equity premium **apart from day 0**, and report a **sign flip to -12.01 bps (t = -1.84)** in
> 2017-2021. Three things follow, each independently disqualifying:
>
> 1. The weeks-2/4/6 design I proposed to satisfy rule 6 removes the **only** component with surviving
>    evidence. My reasoning was exactly backwards.
> 2. The Sharpe of 0.92 below belongs to the **full** even-week strategy, not the 2/4/6 subset. I ran the
>    power gate against a figure that did not belong to the design I specified. Recalculated from the
>    paper's own decomposition, the subset implies Sharpe **0.19** against **0.71** required.
> 3. The 2017-2026 holdout is **burned** - 2017-2021 is now published. Only 2022-2026 is unread, needing a
>    Sharpe of **2.06**.
>
> The analysis below is left unaltered so the error is legible. **No candidate survives Phase 2.**

## Verdict

**SUPERSEDED - see the retraction above.** One candidate was judged to survive: the FOMC-cycle even-week
premium (Cieslak, Morse & Vissing-Jorgensen, JF 2019).
Nine directions were reviewed; eight are rejected, two of them by peer-reviewed rebuttals that refute the
original finding out of sample.

The surviving candidate needs a **decision from Ethan before anything proceeds**, on a duplication question
the protocol does not settle by itself (§5). I am not going to make that call unilaterally, because it is
exactly the kind of judgement that pre-registration exists to force into the open.

---

## 1. What is testable at all — the power frontier

With the corrected gate (`POWER_GATE_AUDIT.md`), at t ≥ 3.5 and 80% power:

| Sample | Hold | Required net Sharpe | Verdict |
|---|---|---|---|
| MNQ 1-min, 7.5y | 1 day | **1.59** | **Refused** — above any published figure |
| Free daily index, 41y | 1 day | 0.55 | Passes |
| Free daily index, 41y | 5 days, ρ = 0.05 | **0.71** | Passes |
| Free daily index, 41y | 21 days, ρ = 0.25 | 1.00+ | **Refused** |
| **Post-publication window only, 10y** | 5 days | **1.37** | **Refused** |

Three conclusions follow, and they constrain everything below:

1. **Nothing can be tested on the 7.5-year MNQ sample.** Budget lines 13 and 14 cannot be spent there.
2. **Only short-hold daily strategies survive.** Anything held a month or longer is refused once overlap and
   autocorrelation are declared honestly. That eliminates most of the obvious candidates by itself.
3. **A ten-year post-publication window cannot clear t ≥ 3.5.** Any out-of-sample check on recent data is a
   *directional* confirmation, not a significance test. This must be pre-committed, not discovered after.

## 2. Candidates reviewed

### C1 — FOMC-cycle even-week premium — **VIABLE, conditional**

| | |
|---|---|
| **Economic rationale** | Equity risk premium is not earned uniformly in time. It concentrates in even weeks of the Fed's ~6-week cycle (weeks 0, 2, 4, 6 from the day before an announcement), which the authors attribute to unexpectedly accommodative Fed news reaching the market — partly through informal channels — and to a "Fed put" that produces mean reversion after declines. The channel is a change in the *risk premium*, estimated to account for ~9 of the 12 bps, not a change in expected cash flows. |
| **Academic support** | Cieslak, Morse & Vissing-Jorgensen, *Stock Returns over the FOMC Cycle*, **Journal of Finance** 74(5), 2019. Peer-reviewed in a top-three journal. |
| **In- or out-of-sample** | **Both, and this is its strongest feature.** Main sample 1994–2016 (184 meetings): even-week days earn ~12 bps/day more than odd-week days, significant at 1%. Pre-sample 1982–1993: smaller but still significant at 10%. Last three years of sample (2014–2016) *stronger*, not weaker. Replicated in developed-ex-US and emerging markets (EM even-week ~17–19 bps vs ~−7 bps odd). Reported Sharpe of holding only in even weeks: **0.92**, against 0.45 for always being long. |
| **Required data** | Daily index closes (free, 1985→) plus a list of scheduled FOMC dates. **The project already has the FOMC date list**, used for H8/H9/H10. No new data purchase of any kind. |
| **Independent observations** | ~984 even-week observations over 41 years (8 meetings/year × 3 even weeks, excluding week 0 — see §5). Non-overlapping at weekly sampling. |
| **Statistical power** | **Passes.** 2,066 non-overlapping observations; required net Sharpe **0.71** against a reported 0.92; required per-observation effect **0.14** against a 0.40 ceiling. The only candidate that clears the gate. |
| **Transaction costs** | ~24 round turns/year (in at each even week, out at each odd week). At the project's audited $0.62/side + 1 tick ≈ $4.48/round turn on 1 MNQ, that is ~$107/year against ~$50,000 notional, about **0.2%/year**. Material but not disqualifying — and unusually, the effect being timed (~3.7 pp/year of excess return) is an order of magnitude larger than the cost, which was *never* true of the twelve intraday hypotheses whose gross edges were smaller than one tick. |
| **Why it might fail** | **(a) Post-publication decay is the central risk**, and the authors themselves raise it: they note the Bernanke–Kuttner and Lucca–Moench findings did not persist in post-publication data. Published 2019 on data to 2016; 2017–2026 is a genuinely clean out-of-sample decade — but §1 shows ten years cannot clear t ≥ 3.5, so a null there is ambiguous. **(b)** Much of the mean-reversion component rests on a small number of days, by the authors' own admission. **(c)** The mechanism is argued from indirect evidence; the authors concede it may partly reflect cash-flow rather than premium effects. **(d)** It is *premium timing*, i.e. long-or-flat on the index — closer to asset allocation than to trading, which `RESEARCH_BUDGET.md` says is better served by the retirement plan. **(e)** The Fed changed its communication regime after 2016 (more press conferences, explicit forward guidance), which could plausibly remove the informal-information channel the paper relies on. |

### C2 — Time-series momentum — **REJECTED on published refutation**

Moskowitz, Ooi & Pedersen (JFE 2012) report a diversified cross-asset Sharpe near 0.8, and TSMOM is the
obvious first thing to try at a daily-to-monthly horizon. **Huang, Li, Wang & Zhou, *Time series momentum:
Is it there?*, JFE 135 (2020) 774–794, refutes it where this project would have to apply it:**

- For **individual assets** — which is what MNQ alone is — only **8 of 55 slopes** are significant at 10%
  (3 at 5%), and **45 of 55 have negative out-of-sample R²**, averaging **−0.67%**.
- The pooled t of 4.34 is below bootstrapped 5% critical values of **12.53** (wild) and **4.83** (pairs), so
  the headline result is not significant once the pooled regression's over-rejection is corrected.
- The diversified portfolio *is* profitable (0.39%, t = 4.73) but is statistically indistinguishable from a
  strategy using only historical means and no predictability at all (difference 0.14%, p = 0.19). The profit
  comes from assets having different mean returns, not from time-series predictability.

A single-market TSMOM test on NQ is therefore a test of something the JFE has already measured as absent in
45 of 55 individual assets. Rejected without spending anything.

### C3 — Volatility management — **REJECTED on published refutation**

Moreira & Muir (JF 2017) scale exposure by the inverse of last month's realised variance and report a ~25%
Sharpe improvement with ~4.9% annual alpha. The rationale is sound: volatility is persistent and
forecastable while expected returns are not, so the return-per-unit-of-risk falls when volatility rises.

**Cederburg, O'Doherty, Wang & Yan, JFE 138 (2020) 95–117, shows it does not survive out of sample, and
specifically not for the market factor** — the closest analogue to a Nasdaq index future:

- Market factor, out-of-sample combination: Sharpe **0.42 managed vs 0.46 unmanaged**. Worse.
- Across 103 strategies: 53 higher, 50 lower — a coin flip. Only 8 significantly favoured management, mostly
  momentum.
- In 72 of 103 cases the out-of-sample certainty equivalent was *lower* than the unmanaged portfolio.
- Cause: structural instability in the spanning-regression parameters. The in-sample alphas require
  information unavailable in real time, so they are not implementable.

Also: a monthly-rebalanced overlay is exactly the hold length §1 shows is refused on power. Rejected twice over.

### C4 — Calendar-spread / basis carry — **REJECTED on power** (`FEASIBILITY_CALENDAR_SPREAD.md`)

Premium probably real (basis predicts futures returns at −4.1 to −5.6, far beyond the −1 convergence
implies), but the tradeable version is cross-sectional across 12+ countries; the single-market timing variant
is Sharpe 0.38, needing 85 years. Also: the owned contract dataset has **0** timestamps with two contracts
quoted at once, so it cannot price a spread at all.

### C5 — Order-flow / microstructure — **REJECTED on data cost**

Needs MBO or MBP-10 depth data, orders of magnitude beyond the $9–10/market spent so far, and available only
from 2017-05-21. H4 already tested an OHLCV-shaped proxy (t 0.71, failed); repeating that would be a
re-parameterisation of a rejected hypothesis, which rule 6 prohibits outright.

### C6 — Variance risk premium / VIX term structure — **REJECTED as untradeable here**

Among the best-documented premia in finance, and genuinely different from all twelve. But harvesting it
requires options or VIX futures. MNQ alone cannot express it, no free daily VIX-futures term structure
exists, and the project has no options approval. On available instruments it is a measurement, not a strategy.

### C7 — Overnight vs intraday return decomposition — **REJECTED as duplicative**

The index earns most of its premium overnight, which is well documented. But H3 (overnight drift 2–3 a.m.,
t −0.74 roll-adjusted) and H7 (overnight-gap reversal, t −0.74) already probed this ground on this
instrument, and the general version is long-or-flat allocation rather than a trading edge.

### C8 — Calendar seasonality (Halloween, sell-in-May, turn-of-year) — **REJECTED on duplication and data mining**

H6 (turn of the month, t 0.45) and H10 (pre-holiday, t 1.70) already tested calendar effects on this
instrument and both failed, including against the random-long-hold benchmark that calendar effects
specifically require. The wider seasonality literature is among the most data-mined in finance, and the
publication-bias work on asset pricing is explicit that such effects are where selection is worst.

### C9 — Cross-sectional equity-index carry or basis — **REJECTED on data cost**

This is the variant the literature actually supports (Koijen 0.91, Hazelkorn 0.83), but it needs a dozen-plus
international index futures. Paid, and far beyond the remaining budget. A cross-section of MNQ/MES/M2K is
*more* correlated than Koijen's regional groupings, which already cut the Sharpe to 0.54.

## 3. Ranking by research feasibility

Ranked by whether the research **can be done credibly**, not by expected profit, as instructed:

| Rank | Candidate | Power | Data | Novel | Rebutted | Status |
|---|---|---|---|---|---|---|
| **1** | C1 FOMC-cycle even weeks | **Pass** | Free, mostly owned | Yes, conditional | No | **Viable** |
| 2 | C6 Variance risk premium | Pass | **Unavailable** | Yes | No | Rejected |
| 3 | C9 Cross-sectional carry | Pass | **Paid, unaffordable** | Yes | No | Rejected |
| 4 | C2 Time-series momentum | Pass | Free | Yes | **Yes, JFE 2020** | Rejected |
| 5 | C3 Volatility management | **Fail** (hold) | Free | Yes | **Yes, JFE 2020** | Rejected |
| 6 | C4 Calendar-spread carry | **Fail** | Partly paid | Yes | — | Rejected |
| 7 | C5 Order flow | Pass | **Paid, unaffordable** | Partly | — | Rejected |
| 8 | C7 Overnight/intraday | Pass | Free | **No** | — | Rejected |
| 9 | C8 Seasonality | Pass | Free | **No** | — | Rejected |

## 4. Rejected directions and the reason, in one line each

| Direction | Rejected because |
|---|---|
| Time-series momentum | 45 of 55 individual assets have negative out-of-sample R² (Huang et al., JFE 2020) |
| Volatility management | Market factor OOS Sharpe 0.42 vs 0.46 unmanaged (Cederburg et al., JFE 2020); and the hold fails the power gate |
| Calendar-spread carry | Needs Sharpe 1.28–1.59; data cannot price a spread (0 overlapping timestamps) |
| Order-flow microstructure | MBO data unaffordable; the OHLCV proxy version is H4, already rejected |
| Variance risk premium | Requires options or VIX futures; not expressible in MNQ |
| Cross-sectional carry | Requires 12+ international index futures; unaffordable |
| Overnight/intraday split | Substantially tested as H3 and H7; and is allocation, not trading |
| Calendar seasonality | Substantially tested as H6 and H10; worst-case publication bias |
| Anything on 7.5y MNQ 1-min | Requires net Sharpe 1.59; above every published figure |

## 5. The decision that is Ethan's, not mine

**Does testing the FOMC cycle violate rule 6?** `RESEARCH_BUDGET.md` prohibits re-testing a rejected
hypothesis "in any re-parameterised form," and H8 was a pre-FOMC hypothesis.

The honest case **for** proceeding: H8 tested a 24-hour window ending 5 minutes before the statement. C1
tests a two-week periodicity across the entire six-week cycle, long-or-flat on daily closes, over 41 years
rather than 7.5, with a different proposed mechanism (risk-premium variation and a Fed put, not pre-meeting
drift). Weeks 2, 4 and 6 are calendar time H8 never touched.

The honest case **against**: both hypotheses key off the same calendar. If the FOMC calendar simply has no
predictive content for this market, C1 is the second attempt to find out, and the family-wise count should
rise accordingly.

**The design that resolves it:** exclude **week 0 entirely** and test only weeks 2, 4 and 6. That removes
every date H8 used, makes the test non-duplicative on its face, and is also the *stronger* test of the paper's
actual claim — if a genuine policy-cycle premium exists, it should appear away from the announcement, not only
beside it. All figures in §2 are computed on that basis.

My recommendation is to proceed **on that restricted design**, but it costs one of two remaining budget
lines and the duplication judgement is yours.

## 6. Recommendation

**Further research is justified, narrowly.** One candidate out of nine, on free data already largely owned,
at a horizon the corrected power gate accepts.

If it proceeds, these must be fixed in the pre-registration **before any data is examined**:

1. Weeks 2, 4, 6 only. Week 0 excluded, to keep clear of H8's dates.
2. Development on 1985–2016 (ending at the paper's sample end). **2017–2026 is the holdout, used once.**
   The split is set by the publication date, not chosen by us — the cleanest holdout boundary this project
   has had.
3. Pre-commit that the 10-year holdout **cannot** clear t ≥ 3.5 (§1: it would need Sharpe 1.37). It is a
   directional check — sign and rough magnitude — and the pre-registration must state what counts as
   confirmation *before* seeing it, or the test is unfalsifiable.
4. Bar t ≥ 3.5 on the development sample, computed on **non-overlapping** weekly observations or with
   Newey-West. No naive t on overlapping daily data (§1, and `POWER_GATE_AUDIT.md` §3).
5. Benchmark against **random long holds of equal exposure**, not against zero. H6, H9 and H10 all looked
   positive until this was applied; a long-or-flat strategy on a market that rose for 41 years will look
   profitable for that reason alone. This is the single most important control for this candidate.
6. Costs imposed at $0.62/side + 1 tick, with a 1×/2×/4× slippage ladder, per `EXECUTION_COST_AUDIT.md`.
7. `t_dropping_best` and an episode-exclusion sensitivity (1987, 2000–02, 2008, 2020, 2022), since a
   41-year result can rest on a few episodes.
8. A **negative control**: the same even/odd test on a calendar with no policy content — e.g. weeks offset
   from FOMC dates by a fixed number of weeks — mirroring the placebo design that is the strongest evidence
   H8 ever produced.
9. Index caveats from `DATA_QUALITY_DAILY.md` §2 and §6 stated explicitly: price-return only, no dividends,
   no financing, and the pre-1999 period is not a tradeable-contract claim.

**If Ethan judges that rule 6 bars it, then no candidate survives Phase 2, and that is the result.** The
project would conclude with 0 of 12 plus a documented statement that the search space reachable on available
data and at a defensible bar is empty — which is a real finding, and better supported than most published
ones.

## What this phase actually produced

No strategy, and that is the point. What it produced instead: a power gate that refuses its own author's
first draft and the sample behind this project's best-ever result; measured evidence that a monthly-hold
daily study clears t ≥ 3.5 on pure noise 22% of the time; two candidates killed by peer-reviewed rebuttals
found before any code was written; and one survivor with a pre-set holdout boundary.

Four candidates were eliminated on **published out-of-sample refutations**, not on this project's data. That
is the cheapest possible way to learn they do not work, and it is what the infrastructure is for.
