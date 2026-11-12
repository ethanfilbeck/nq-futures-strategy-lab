# Feasibility: calendar-spread carry on MNQ — NOT TESTABLE AT THIS PROJECT'S BAR

Written 2026-11-11. This is a **feasibility report, not a strategy and not a pre-registration.** No paid data
was accessed, no download was initiated, and no strategy code was modified in producing it.

## Verdict

**No-go.** The hypothesis is economically real, academically supported, and genuinely different from the twelve
hypotheses already tested. It fails on **statistical power**, and it fails before any data is examined.

Taking the published literature entirely at face value, and assuming the effect transfers to MNQ perfectly,
the available 7.5 years of history cannot produce a t-statistic at this project's bar of 3.5:

| Published variant | Sharpe | t reachable in 7.5y | Years needed for t = 3.5 |
|---|---|---|---|
| Koijen et al. 2018, equity carry, **cross-section of 13 indices** | 0.91 | 2.49 | 14.8 |
| Koijen et al. 2018, equity carry, region-grouped | 0.54 | 1.48 | 42.0 |
| Hazelkorn et al. 2020, equity basis, **cross-section** | 0.83 | 2.27 | 17.8 |
| Hazelkorn et al. 2020, equity basis, **timing (single market)** | 0.38 | 1.04 | 84.8 |

To clear t = 3.5 in 7.5 years requires a Sharpe of **1.28**. No equity-index carry or basis variant in either
paper reaches that. It is higher even than Koijen et al.'s *diversified, all-asset-class* global carry factor
(1.20), which is the best-performing portfolio in that paper.

The decisive point is the last row. **Both papers' strong results are cross-sectional** — long cheap index
futures, short expensive ones, across a dozen or more countries. MNQ alone has no cross-section. The variant
that applies to a single market is the *timing* strategy, and that is the weakest one in the table: Sharpe
0.38, which would need **85 years** of data.

This project's own rules then settle it. `docs/RESEARCH_BUDGET.md` rule 3 fixes the bar at t ≥ 3.5 and says
it does not fall. A test that cannot reach its bar even if the hypothesis is true is not a test. Spending a
budget line on it would buy an uninformative null — the one outcome the protocol exists to prevent.

Per the instruction that opened this assessment: the answer to "is there enough independent historical data"
is **no**, so **no money should be spent collecting additional data.**

---

## 1. Repository and dataset review

Verified against the repository at `d2480f7`, not against earlier summaries.

| Asset | What it is | Bearing on this hypothesis |
|---|---|---|
| `data/mnq_contracts.csv` | 250,846 1-min bars, **31 individual MNQ contracts**, MNQM9–MNQZ6 | Cannot price a spread — see §5 |
| `data/mnq_train.csv`, `mnq_holdout.csv` | Volume-rolled **continuous** MNQ | One leg only |
| `data/mes_*`, `m2k_*`, `mgc_*`, `nkd_*` | Continuous series, four more markets | One leg each |
| `docs/AUDIT_2026_11_ROLLS.md` | 12 roll gaps measured on MNQ, 2022-09 to 2025-06 | **The only spread data owned** — see §3 |
| `nq_bot/rolls.py`, `scripts/roll_map.py` | Roll detection; exact roll dates from symbology | Reusable infrastructure |
| `docs/QUANTITATIVE_RESEARCH_LITERATURE_REVIEW.md` §229 | Already flags "daily settles, front + second contract" as the carry data path at ~$1–3/market | Consistent with §6 |

## 2. How equity-index futures calendar spreads work

A futures price is tied to spot by cost of carry. For an equity index paying dividends:

```
F(T) = S · exp[ (r − q) · T ]
```

where `r` is the financing rate to expiry and `q` the expected dividend yield over the same horizon. The
calendar spread between two listed quarters is the difference of two such prices:

```
F(T2) − F(T1) ≈ S · (r − q) · (T2 − T1)
```

So the spread is, to first order, **a financing instrument.** It is the market's price of borrowing to hold
index exposure for three months, net of the dividends forgone. Four things move it:

- **Financing rates.** The dominant term. Higher `r` widens the spread roughly linearly.
- **Expected dividends.** Nasdaq-100 yield is low (~0.7%), so `r` dominates for MNQ far more than it would
  for a high-yield index. This is also why the gold control's rolls are nearly flat (no dividends, and gold
  carry is near zero): measured median **+0.11%** versus MNQ's +0.64% to +1.38%.
- **Time to expiry.** The spread decays mechanically toward zero as T1 approaches, which is convergence, not
  a return.
- **Rolls.** Because the continuous series splices without back-adjustment, each roll prints the spread as a
  one-minute jump. That artifact is what contaminated H8, and correcting it is what produced this project's
  only spread measurements.

Everything above is **mechanical.** None of it is tradeable: a trader who buys the spread and holds it to
expiry earns the carry and pays the financing, and the two cancel by construction. A strategy needs the
*residual* — the deviation of the observed spread from this fair value.

## 3. Could a premium exist beyond mechanical fair value?

**Yes, and this is the strongest part of the case.** It is not hand-waving, and it has an identified
mechanism, which is why this hypothesis deserved a serious assessment rather than a one-line dismissal.

Hazelkorn, Moskowitz & Vasudevan (2020) measure the equity futures basis — futures price minus synthetic
fair value, expressed as an implied financing rate — for 18 developed equity indices, 2000–2017:

- The average basis is about **−1 bp**, i.e. fair value holds *on average*, exactly as the identity predicts.
- But average **absolute** basis is **57 bp**, with time-series and cross-sectional standard deviations near
  **92** and **90 bp**. Fair value holds on average while being violated substantially at any given moment.
- The basis **negatively predicts futures returns**, with panel coefficients of roughly **−4.1 to −5.6.**
  This is the key number. Pure convergence to fair value implies a coefficient of about −1. Coefficients four
  to five times that size mean returns move far more than convergence explains, so something beyond mechanics
  is being compensated.
- The proposed mechanism is **uninformed leverage demand** met by capital-constrained dealers. Dealer net
  positioning is strongly negatively related to the basis (1 SD ≈ **−29 bp**), and securities-lending costs
  move it too (a 1% rise in lending fee ≈ **−29 to −35 bp**).

Koijen, Moskowitz, Pedersen & Vrugt (2018) reach a compatible conclusion from the carry side: equity-index
carry, defined forward-looking from futures prices as expected dividend yield minus the local risk-free rate,
earns a Sharpe of **0.91** (mean 9.58%, sd 10.48%) across 13 country index futures from 1988/2000–2012 —
stronger than commodities (0.60), currencies (0.68) or Treasuries (0.68).

**So the premium is probably real.** The problem is not whether it exists. It is that neither paper's
tradeable version is available to this project, for the reasons in §5 and §7.

### What contradicts it

- Both headline results are **cross-sectional**, and the paper that reports a single-market timing variant
  puts it at Sharpe **0.38** — a quarter of the cross-sectional alpha's economic weight.
- Koijen et al.'s own robustness check cuts the Sharpe to **0.54** when the 13 indices are collapsed into
  correlated regional groups. Fewer, more-correlated units means a weaker result. A cross-section of
  MNQ/MES/M2K is *more* correlated than Koijen's regions, not less, so it would land below 0.54, not above
  0.91. This closes the obvious loophole of building a cross-section from markets already owned.
- Hazelkorn et al. is an **unrefereed NBER working paper**, and two of three authors are at AQR, which sells
  strategies of this family. That is not disqualifying, but it is not peer review either.
- The equity basis is described as **short-lived**, consistent with a liquidity premium that is harvested by
  dealers with balance sheet, not by a retail account with one micro contract.
- Stock-index futures arbitrage is among the most-studied anomalies in the literature, and the general
  finding across that body of work is that measured mispricing has **shrunk over time** as execution
  improved — so 2019–2026 is the least favourable window, not the most.

## 4. Academic record

| Work | Status | Bearing |
|---|---|---|
| Hazelkorn, Moskowitz & Vasudevan, *Beyond Basis Basics*, NBER WP 26773 (2020) | Working paper, unrefereed | **Supports** a premium; mechanism identified; but XS Sharpe 0.83 vs timing 0.38 |
| Koijen, Moskowitz, Pedersen & Vrugt, *Carry*, JFE 127(2) (2018) 197–225 | Peer-reviewed | **Supports** equity carry at Sharpe 0.91 — but cross-sectional across 13 countries |
| Koijen et al., region-grouped robustness | Peer-reviewed | **Contradicts** transfer to a small correlated cross-section (0.54) |
| Stock-index futures arbitrage literature | Peer-reviewed, large | **Contradicts** — mispricing documented but declining with execution quality |

No claim is made here that any of these proves an edge exists in MNQ. They establish that the *question* is
legitimate; they do not establish an answer for this instrument.

## 5. Is the existing MNQ dataset sufficient? **No — and the reason is categorical**

A calendar spread requires **both legs quoted at the same instant.** The contract-level dataset does not
contain a single such moment:

```
contracts:                           31
timestamps total:               250,846
timestamps with >=2 contracts:        0      <-- decisive
max contracts at one timestamp:       1
```

This is not a defect. `scripts/fetch_contract_windows.py` was deliberately cost-gated to fetch each
contract only over the window in which it was the front month, because H8 needed the contract actually held.
Those windows **tile** the timeline; they never overlap. The dataset is correct for its purpose and
structurally unusable for this one.

The continuous series are worse: a volume-rolled continuous symbol is by construction a *single* leg.

The only spread observations this project owns are the **12 roll gaps** in `AUDIT_2026_11_ROLLS.md`
(+0.64% to +1.38%, 2022-09 to 2025-06). Those are 12 point-in-time snapshots, one per quarter, each at a
single minute. Twelve numbers cannot support a return-predictability test, and their magnitudes track
interest rates — which is to say they look like pure cost of carry, with no visible residual.

## 6. Does it require additional instruments or paid data? **Yes, but cheaply**

This is worth stating plainly because cost is *not* the obstacle here:

- **Needed:** daily settlement prices for the front and second MNQ contract, both legs, 2019–2026. Daily is
  sufficient — a carry trade holds for weeks, so 1-minute resolution would be waste.
- **Scale:** two legs × ~1,890 trading days ≈ 3,800 daily records, versus the 250,846 one-minute bars already
  bought for **$0.9158** (a measured $3.65 × 10⁻⁶ per record). The marginal data cost is on the order of
  **$1–3**, matching the estimate already recorded in the literature review.
- **Also needed:** a term financing benchmark (SOFR/OIS) to compute fair value, and expected-dividend data or
  a futures-implied proxy.
- **Also needed for the cross-sectional variant:** a dozen-plus international index futures. That is well
  beyond this project's remaining budget and is the variant the literature actually supports.

So the money is trivial and the money is not the reason to stop. **Power is.** Spending $3 to run a test that
cannot reach its own bar is still a wasted budget line, and under rule 3 the bar does not move to accommodate
it.

## 7. Independent observations available

This is the binding constraint, and it is worse than the raw count suggests.

- **Quarterly cycles, 2019-05 to 2026-11: 30.** A quarterly-held spread trade yields ~30 observations. To
  clear t = 3.5 on 30 observations requires a per-trade mean/sd of **0.64** — a 0.64-SD edge repeated every
  quarter for seven years. Nothing in the literature is remotely that strong.
- **Daily observations (~1,890) do not help.** The basis is driven by financing rates, which are
  *persistent*. Overlapping daily readings of a slow-moving variable are not independent trials; the
  effective count collapses back toward the number of rate regimes, not the number of days.
- **And over this specific window there are about three rate regimes, not thirty.** Policy rates went ~2.4%
  → ~0.05% (2020) → ~5.5% (2023) → ~4% (2025–26). Since the spread is mechanically near-linear in `r`, the
  entire "signal" over 2019–2026 is essentially one slow macro variable traversed three times. The effective
  independent sample on the thing being tested is **single digits.**

That last point is the deepest version of the problem, and no amount of extra data purchased *within this
window* fixes it. The fix would be a longer history spanning more rate cycles, which for MNQ does not exist
(the contract launched in 2019).

## 8. Confounds, bias and execution risks

Documented in advance, as the protocol requires, even though the hypothesis is not proceeding:

1. **Rate regime as a lurking variable (severe).** Spread level and spread *changes* are both functions of
   `r`. Any apparent predictability may be a rate-forecasting result in disguise, and a rate-forecasting
   result on three regimes is noise.
2. **COVID (March 2020) dominance.** The equity basis dislocated violently in that episode. A single
   fortnight could carry an entire 30-observation result. Any test would need `t_dropping_best` from
   `research_report.py` and an explicit exclusion sensitivity — and on 30 observations, dropping the best one
   is a large perturbation.
3. **Look-ahead via revised series.** Both SOFR/OIS histories and dividend data are subject to revision and
   to as-of ambiguity. Fair value must be built only from information available at the decision time.
   Deriving carry from futures prices (Koijen et al.'s approach) avoids this and is the correct method.
4. **Settlement-time mismatch.** Legs must be priced at the same instant. Mixing a front-month settle with a
   back-month last-trade manufactures a spurious spread series — a close cousin of the roll artifact that
   contaminated H8, and the single most likely way this research would fool itself.
5. **Back-month liquidity (severe for execution).** The second MNQ contract is thin outside the roll window.
   The project has already been burned by exactly this: the Nikkei replication was invalidated on bar
   coverage after $6.25 was spent, which is why `scripts/preflight_coverage.py` now exists. Any version of
   this research must run that preflight on the **back month** first. A published basis premium measured on
   institutional-size E-mini and index markets does not transfer to a retail micro back-month book.
6. **Execution cost on two legs.** A spread is two contracts, so round-trip cost roughly doubles to ~$4.48
   against the project's audited $2.24/contract. Small against a 1% carry, but the tradeable quantity is the
   *residual*, which is a fraction of that.
7. **Multiple testing.** The hypothesis space is wide — which legs, which fair-value model, which holding
   period, which signal threshold. The 12-strategy family already carries a familywise burden
   (`PBO_ANALYSIS.md`: effective trials 11.33 of 12, mean |pairwise correlation| 0.036). Adding a
   lightly-constrained new family to a 30-observation sample is how backtest overfitting happens.
8. **Survivorship/definition drift.** MNQ's listed cycle and the liquidity migration point change over the
   sample; "the second contract" is not a constant object.

## 9. How it could be falsified

Stated for completeness, since a hypothesis that cannot be falsified should not be entertained at all:

- **Primary:** regress forward spread-trade returns on the fair-value residual. Pure mechanics predicts a
  convergence coefficient of about −1 and no alpha. A coefficient materially beyond −1 with significant
  alpha, as Hazelkorn et al. report, supports a premium; a coefficient near −1, or an insignificant one,
  falsifies it.
- **Negative control:** the same construction on **MGC** (gold), where measured roll gaps are +0.11% and
  dividend/lending mechanisms are absent. A "premium" that appears in gold as strongly as in MNQ is a
  construction artifact, not a premium. This mirrors the gold control already used for H8.
- **Placebo:** shift the signal by one quarter. The effect must vanish.
- **Pre-committed failure:** t < 3.5 on the pre-registered rule, or any result that reverses when the single
  largest contributing episode is dropped, is a published failure.

**This is a well-formed, falsifiable research design. It is simply not powered.** Writing it out makes that
concrete: every element above is sound, and the test would still be a coin-flip dressed in a t-statistic.

## 10. Is it sufficiently different from the twelve already tested? **Yes**

Genuinely so, which is why it was worth assessing:

| | The twelve | Calendar-spread carry |
|---|---|---|
| Traded object | Direction of outright price | The **term structure** between two contracts |
| Horizon | Minutes to one day | Weeks to a quarter |
| Economic claim | Behavioural/flow patterns in intraday price | A **financing and risk-transfer premium** |
| Source of return | Price change | Residual from a fair-value identity |
| Correlation with existing family | Near zero by construction | Near zero by construction |

Novelty is not the problem. This hypothesis clears rule 1 of the budget (it comes from published research,
not from looking at this data) and it clears rule 6 (it is not a re-parameterisation of anything rejected).
It fails on power alone.

One caveat worth recording: `RESEARCH_BUDGET.md` already rules out "longer horizons (multi-day to weekly)"
as *eligible but better served by the retirement-account plan than by this bot*. A quarterly-held financing
trade sits squarely in that category. Even if it were powered, it is closer to asset allocation than to the
intraday automation this bot was built for.

## Recommendation

1. **Do not spend a budget line.** Remaining lines stay at 2.
2. **Do not purchase data.** The $1–3 is affordable and still wasted.
3. **Do not pre-register.** A pre-registration implies an intent to test; the honest finding is that the test
   is not available at this bar on this instrument's history.
4. **Record this as a closed direction** in `RESEARCH_BUDGET.md`, with the power table as the reason, so that
   neither this project nor a future one re-opens it without new information.
5. The direction becomes live again only under conditions that do not hold today: a longer MNQ history
   spanning more rate cycles, a genuine multi-country cross-section, or a bar lower than 3.5 — and lowering
   the bar is prohibited.

## What this does not say

It does not say calendar-spread carry is unprofitable. The evidence in §3 suggests a real premium exists and
is earned by someone. It says **this project cannot demonstrate it**, which is a different and more honest
claim. The distinction matters: "we found no edge" and "we could not have found this edge if it were there"
are not the same result, and only the second is true here.
