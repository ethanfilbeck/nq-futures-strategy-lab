---
name: power-check
description: Work out whether a sample can support a statistical bar before testing. Use when asked if a result is significant, how many trades or years are needed, or whether a backtest, track record or posted P&L proves anything.
---

# Can this sample reach that bar?

```
py scripts\preflight_power.py --years 30 --bar 3.5 --hold-days 5 --autocorr 0.05
py scripts\preflight_power.py --observations 59 --bar 3.5
```

## The arithmetic, which does not depend on the hypothesis

A t-statistic on an annualised Sharpe `S` over `T` years is about `S·√T`. To clear a bar `B` with probability
`power`:

```
S  >=  (B + z_power) / sqrt(T)  *  sqrt((1 + rho) / (1 - rho))
```

Without the `z_power` term you get the Sharpe for a **coin flip**, not a test. Verified by Monte Carlo:
at the 50%-power figure, `P(t >= 3.5)` measured **50.1%**.

| Sample | Required net Sharpe, t ≥ 3.5, 80% power |
|---|---|
| 7.5 years (MNQ 1-min) | **1.59** |
| 16 years | 1.09 |
| 30 years | 0.79 |
| 41 years | 0.68 |

For scale, documented net Sharpes top out near **0.9** for a single liquid index future traded
directionally. So the 7.5-year sample cannot clear t ≥ 3.5 for *any* published effect size.

## For judging someone else's posted results

Per-observation form: a sample of `n` needs `(3.5 + 0.84)/√n` standard deviations **per trade**.

| n | required effect | verdict |
|---|---|---|
| 18 | 1.02 | far beyond any real strategy |
| 24 | 0.89 | same |
| 33 | 0.76 | same |
| 59 | 0.57 | refused — this is H8's own sample |
| **118** | **0.40** | the minimum that is even arguable |

The credible ceiling is **0.40**; H8, the strongest of twelve hypotheses, measured **0.33**. A posted track
record of 18–40 trades cannot distinguish an edge from a good week — not for the viewer and **not for the
person posting it**.

Total P&L without a denominator says nothing. Ask for: number of trades, period, account size, **max
drawdown**, and the worst single trade. If drawdown is never shown, that is usually the reason.
