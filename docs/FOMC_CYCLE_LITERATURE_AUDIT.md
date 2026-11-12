# Independent literature audit: FOMC-cycle even-week candidate — **REJECTED**

Written 2026-11-11, hours after the candidate was proposed in `RESEARCH_PHASE2_DAILY.md`.

## Conclusion: REJECTED

**The published evidence contradicts the candidate**, and it contradicts it most sharply in exactly the
design I proposed to make it clear this project's duplication rule. The candidate is not profitable, not
validated, and not researchable.

The decisive source was verified independently, not taken on report:

> Knox, Benjamin, and Annette Vissing-Jorgensen (2026). "The Effect of the Federal Reserve on the Stock
> Market: Magnitudes, Channels and Shocks." Finance and Economics Discussion Series 2026-023, Board of
> Governors of the Federal Reserve System. DOI: 10.17016/FEDS.2026.023. Also Annual Review of Financial
> Economics.

**Vissing-Jorgensen co-authored the 2019 original.** This is not an outside critique; it is one of the
original authors revising her own finding with twelve more years of data and a decomposition the first paper
did not have. Their own summary judgement:

> it is unlikely that the even-week pattern over the FOMC cycle represents an equity premium

---

## 1. Does the weeks 2/4/6 effect survive the later research? **No**

Knox & Vissing-Jorgensen find **no evidence of a systematically higher equity premium on even-week days
apart from the higher day-0 premium.**

The weeks 2/4/6 subset is, by construction, the even-week days *other than* day 0. It is precisely the set
the later paper says carries no premium evidence.

## 2. Does excluding week 0 resolve the later paper's concerns? **No — it inverts them**

This is the finding that matters, and it is a correction to my own reasoning.

I proposed excluding week 0 to keep clear of H8's dates and satisfy `RESEARCH_BUDGET.md` rule 6. I described
that as "the stronger test of the paper's actual claim, since a real policy-cycle premium should appear away
from the announcement."

**That reasoning was exactly backwards.** Day 0 is the *only* component with surviving premium evidence.
Removing week 0 does not strengthen the test; it deletes the one part that survived and keeps only the parts
that did not. My proposed design was the weakest possible version of the candidate, and I presented it as
the most defensible one.

## 3. Original sample versus genuinely post-publication evidence

The distinction the original paper's own numbers obscure:

| Period | Status | Even-week excess return | t |
|---|---|---|---|
| 1994–2016 | **Original sample** (CMVJ 2019) | **+11.48 bps/day** | **3.83** |
| 2017–2021 | **Genuinely post-publication** | **−12.01 bps/day** | **−1.84** |

The sign flips, at nearly equal magnitude. The authors describe 2017–2021 as a "statistically significant
opposite cycle in stock returns, with average returns lower in even weeks," attributing it to Fed news
arriving worse than expected.

**Being precise about strength, in both directions:** t = −1.84 is significant at the **10%** level only, so
the reversal is suggestive rather than conclusive, and I will not overstate it the way I overstated the
original. The component that is strongly significant is the cash-flow-and-equity-premium part at
**−21.57 bps (t = −2.03)**. What the reversal establishes is not "the effect is negative" but something that
is fatal anyway: **the sign is not stable out of sample.**

### The decomposition is the deeper problem

Knox & Vissing-Jorgensen break the 1994–2016 effect into channels:

| Channel | bps/day | t |
|---|---|---|
| Total even-week excess return | 11.48 | 3.83 |
| — from **yield declines** | **6.08** | 1.92 |
| — from cash flow + equity premium | 5.88 | 1.19 |
| — from equity premium, years 1–2 | 2.36 | 2.75 |

The majority of the effect comes from **yields falling**, and Nagel & Xu (2024) put it at 5.8 of 8.2 bps
over the longer 1994–2023 window. A realised path of falling yields over a twenty-year bond bull market is
not a harvestable risk premium — it is a regime that happened once and cannot repeat from a 4% starting
point the way it did from 8%.

This is the same lurking variable that closed calendar-spread carry: **the rate path, masquerading as an
effect.** Finding it twice in two different candidates is itself informative about where this search keeps
going wrong.

## 4. Is the Sharpe of 0.92 applicable to weeks 2/4/6? **No, and I misapplied it**

0.92 is the Sharpe of the **full even-week strategy** — holding the market in weeks 0, 2, 4 and 6 — against
0.45 for always being long. Week 0 contains both the day-0 premium and the pre-FOMC drift, which the 2026
paper identifies as the only robust components.

So 0.92 cannot be attributed to the 2/4/6 subset. **My Phase 3 report ran the power gate against 0.92 while
specifying a weeks-2/4/6 design.** The gate "passed" a Sharpe that did not belong to the strategy described.
That is a material error on my part and it is the reason the candidate appeared to survive at all.

## 5. Can S&P 500 findings be generalised to the Nasdaq-100? **Unfavourably**

The paper uses **S&P 500 excess returns over T-bills from CRSP**, noting the pattern is similar for the
total market. The Nasdaq-100 is a different object: ~100 names, heavily concentrated in large-cap
technology, higher beta, and much longer duration in the equity-duration sense.

A pure risk-premium timing effect might scale roughly with beta. But the dominant channel here is **yield
declines**, and long-duration growth equities are *more* rate-sensitive than the broad market, not less. So
the NDX version of this strategy would be **more** exposed to the rate-regime confound, not better
insulated from it. Generalisation does not help the candidate; it concentrates its single biggest weakness.

## 6. Does the 2017–2021 reversal invalidate the directional holdout? **Yes, completely**

My proposed design developed on 1985–2016 and held out 2017–2026, with the split set by the paper's
publication date rather than chosen by us. I described that as the cleanest holdout boundary this project
has had.

**It no longer exists.** 2017–2021 has now been read, published, and reported with a flipped sign. A holdout
whose answer is in the literature is not a holdout. What remains unread is 2022–2026:

| Window | Status | Required net Sharpe (t ≥ 3.5, 80% power, 5-day hold) |
|---|---|---|
| 2017–2026, as planned | **Burned** — 2017–2021 is published | 1.44 |
| 2022–2026, the only unread data | Available | **2.06** |

A Sharpe of 2.06 is roughly double the highest figure in the entire reference table. **The candidate has no
usable out-of-sample test left**, and that alone is disqualifying under this project's rules regardless of
everything above.

## 7. Recalculated power, with the corrected gate

Taking the only premium-attributable component the paper isolates (2.36 bps/day, t = 2.75) as the honest
expected effect for a weeks-2/4/6 design:

| | |
|---|---|
| Premium-attributable effect | 2.36 bps/day on ~126 even-week days/year |
| Implied incremental return | **2.97%/year** |
| Long-or-flat strategy volatility | ~15.6% (NDX ~22%, in the market about half the time) |
| **Implied Sharpe** | **0.19** |
| **Required** (41 years, 5-day hold, ρ = 0.05, 80% power) | **0.71** |
| Verdict | **REFUSED** |

0.19 against a requirement of 0.71. The gate refuses it by a factor of nearly four, and it refuses it using
the paper's own decomposition rather than any assumption of mine.

## 8. Is the candidate genuinely independent of H8? **No — and the structure is a trap**

The two branches are exhaustive and both fail:

- **Test week 0** (where the surviving evidence is) → that is the pre-FOMC window and the day-0 premium,
  i.e. substantially H8. Rule 6 prohibits it, and H8 has already failed on this project's own data: t 2.50
  on training against a 3.0 bar, **−0.27 on the holdout**, priced on the contracts actually held.
- **Exclude week 0** (to be independent of H8) → the remaining weeks 2/4/6 are where the later paper finds
  no premium, and where the recalculated power is 0.19 against 0.71.

**The component with evidence is not independent of H8. The component that is independent of H8 has no
evidence.** There is no version of this candidate that is both admissible under rule 6 and supported by the
literature.

---

## My process failed here, and the failure is worth recording

I searched for post-publication rebuttals of time-series momentum and found Huang et al. (2020). I searched
for rebuttals of volatility management and found Cederburg et al. (2020). I rejected both on that basis, and
wrote in the Phase 3 report that finding published refutations before writing code "is the cheapest possible
way to learn they do not work."

**I did not run that same search on the candidate I wanted to keep.** The asymmetry is the whole story: I
applied adversarial scrutiny to the hypotheses I was discarding and not to the one I was advancing. The
refuting paper was findable, it is co-authored by one of the original authors, and it is published by the
Federal Reserve. Ethan found it; I should have.

That is textbook confirmation bias, and it is more dangerous than the roll contamination, because roll
contamination was a bug in code that tests eventually caught, whereas this was a gap in *what I chose to
check* — the kind of error that no test suite catches and that produces a plausible, well-cited,
well-documented recommendation that happens to be wrong.

**The fix, added to `RESEARCH_PROTOCOL.md`:** a surviving candidate requires a documented
post-publication-refutation search **before** it may be called researchable, including a search for later
work by the original authors. A candidate that has not survived a deliberate attempt to refute it has not
survived anything. Failing to find a rebuttal must be recorded as a search that was run, with its terms, not
left as an absence.

## Where this leaves the project

**No candidate survives Phase 2.** Nine were reviewed; all nine are now rejected.

The research record stands at **0 of 12**, with these additions:

- Calendar-spread carry: closed on power.
- Time-series momentum: closed on a JFE refutation (45 of 55 individual assets negative out-of-sample R²).
- Volatility management: closed on a JFE refutation (market factor 0.42 managed vs 0.46 unmanaged).
- FOMC-cycle even weeks: closed on a Federal Reserve paper by an original author, plus a holdout that no
  longer exists and a recalculated Sharpe of 0.19 against 0.71 required.
- Five further directions closed on data cost, instrument availability, or duplication.

Two independent candidates have now been closed by the same lurking variable — **the realised path of
interest rates over 1994–2016 or 2019–2026, mistaken for an effect.** That recurrence is probably the single
most useful finding of this phase, and it would apply to any future candidate keyed to a macro calendar.

The honest reading is that the project's search is finished. The infrastructure works: it refused its own
author's gate, refused this project's best-ever hypothesis, and in this phase killed every candidate before
a single line of strategy code was written or a dollar spent. What it did not produce is an edge, and on the
evidence now assembled that is the correct output rather than a shortfall.
