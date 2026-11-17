# Literature review: overnight vs regular-session behaviour

Written 2026-11-11, before any session-level statistic was computed on this project's data.

## Access status: read this first

The brief says not to rely on abstracts when full papers are available. Here is exactly what was read:

| Paper | What was read | Status |
|---|---|---|
| Bondarenko & Muravyev, JFQA 58(3) 2023 | **Full working paper** (Mar 2020, NFA conference copy): tables 1, 3–6 | Verified from full text |
| Boyarchenko, Larsen & Whelan, RFS 36(9) 2023 | NY Fed Staff Report 917 front matter + both Liberty Street posts (May 2021, **July 2026**) | Partly verified |
| Liu & Tse, IREF 48 (2017) 440–451 | Abstract plus secondary descriptions in citing papers | **Full text not reachable** (Elsevier paywall; Academia/ResearchGate copies refused the fetch) |
| Riedel & Wagner, JIFMIM 39 (2015) 53–64 | Abstract (SSRN and Elsevier) plus citing papers | **Full text not reachable** (SSRN and ResearchGate refused the fetch) |

**Action for Ethan:** Murray State's library should have ScienceDirect access to both Elsevier papers. Before
the protocol is frozen, pull both PDFs and check the five items marked *unverified* below. **The protocol is
written so that no test depends on an unverified number.** The two papers supply only the direction of a
prediction, and both directions are also in the abstracts.

---

## 1. Liu & Tse (2017), *Overnight returns of stock indexes: evidence from ETFs and futures*

| | |
|---|---|
| Market / instruments | US index **ETFs** and **12 international index futures** (per Jin et al.). *Unverified:* whether QQQ or NQ is among them, and how "overnight" is defined for futures (pit or regular-session close → open, or Globex). |
| Sample | 1999–2014 |
| Method | Session means and volatilities; copula-based VaR/ES; predictive regressions of first and last half-hour returns on the overnight return, with an out-of-sample check |
| Findings | Overnight returns significantly positive for US ETFs and most index futures; trading-hours returns negative. **Overnight volatility lower than trading volatility.** For SPY, a mean of about +0.035%/day overnight vs −0.012%/day intraday (from a secondary summary; *unverified*). |
| In / out of sample | Session statistics are in-sample. Only the half-hour predictability is tested out of sample. |
| Later contradicting work | Lachance (JFM 2021): order imbalances and wider overnight spreads **inflate ETF overnight returns by over 6% a year**, so the ETF part of the premium is partly microstructure. Boyarchenko et al. (2026, below): the futures overnight premium has gone flat since 2021. |
| Relevance to NQ | **Volatility finding: likely general.** Mean-return finding: the ETF part does not carry over to futures. The half-hour predictability overlaps H1 and H7, both rejected on this data, so it is excluded here. |

## 2. Bondarenko & Muravyev (2023), *Market return around the clock: a puzzle*

| | |
|---|---|
| Market / instruments | **E-mini S&P 500 (ES)** front month, TickData 1-minute bars; quotes for 2010–2018 |
| Sample | 2004–2018. Half-days and holidays excluded. |
| Method | Log returns summed by window, annualised ×252; t-statistics robust to heteroskedasticity and autocorrelation (exact estimator not named); moving one-hour and four-hour windows; Bonferroni check; a European-DST natural experiment |
| Findings | "EU-open" (11:30 pm–3:30 am, labelled EST) earns **7.60%/yr (t 6.35, Sharpe 1.67)**. Rest of day earns **−0.80% (t −0.17)**. The whole day earns 6.80% (t 1.39). Annualised volatility by session: Asia 0.14, EU-open 0.16, Europe 0.20, **US 0.32**. The US session carries about **60% of daily variance**, and the 10 hours from US close to EU-open about 10%. |
| In / out of sample | Single in-sample period. EU-open is significant at 5% in **9 of 15** years. Their conditional strategy is not tested in a formal out-of-sample exercise. |
| Internal inconsistencies noticed | Table 1 caption 7.42% vs table 7.60%. EU-open variance share given as 5–10% in one place and 8% in another. The text says significant for every weekday and month, but Monday (t 1.63), January (0.83) and October (0.50) are not. |
| Later contradicting work | Boyarchenko et al. (2026): the closely related 2–3 a.m. window has been flat in 2021–2025, **including in NQ**. |
| Relevance to NQ | The paper says outright that **E-mini Nasdaq-100 futures were illiquid outside US hours** in its sample, and it gives no NQ results. The ES variance shares are a benchmark, not a prediction for NQ. The session-volatility ordering (US > Europe > Asia) is likely general. The return concentration is the claim this project already tested as H3; it decayed and is not re-tested here. |

## 3. Riedel & Wagner (2015), *Is risk higher during non-trading periods?*

| | |
|---|---|
| Market / instruments | Major **cash stock indexes** of the US, France, Germany and Japan, at daily frequency (open/close). *Unverified:* exact index list and sample dates. |
| Method | GARCH for conditional returns of close–close, intraday and overnight components; Generalized Pareto Distribution for the innovations; tests of fat tails and of tail-index equality; conditional VaR |
| Findings | **Overnight innovations show significant tail risk; intraday innovations do not.** Overnight downside risk is a moderate volatility component plus a significant tail component. |
| In / out of sample | In-sample estimation. *Unverified:* any VaR backtest. |
| Later contradicting work | No direct replication found (searches below). Lockwood & McInish (JBF 1990) find variability higher intraday in both bull and bear markets, but they do not test vol-scaled tail shape. |
| Relevance to NQ | **This is the most transferable *open* question, with one important caveat.** The paper's mechanism is a *non-trading* period: information piles up while nothing trades, so the open reprices it in one jump. **NQ trades through the night on Globex**, so the jump mechanism is weakened. If NQ overnight returns are *not* fat-tailed after volatility scaling, that fits the mechanism rather than contradicting the paper. The question is worth testing for exactly that reason. |

## 4. Additional independent research

| Paper | Instrument / sample | Relevant finding | Use here |
|---|---|---|---|
| Boyarchenko, Larsen & Whelan, *The Overnight Drift*, RFS 2023 | ES, 1998–2018/2020 | 2–3 a.m. ET earns ~3.6–3.7%/yr. Linked to dealers absorbing closing order imbalances. | Already tested as H3 (reproduced, then decayed). Not re-tested. |
| **Same authors, *The Disappearing Overnight Drift*, Liberty Street, July 2026** | ES 2021–2025 (1,245 days); says NQ and YM match | **Drift "close to zero" since 2021.** The authors attribute this to closing-imbalance dispersion falling by more than half (6.5% → 2.9%). No standard errors are given. | **Original authors revising their own finding.** It confirms what H3 found and is the reason mean returns are not a primary claim here. |
| Lachance, JFM 2021 | US ETFs | Microstructure inflates ETF overnight returns by more than 6% a year | ETF results don't transfer to futures |
| Lou, Polk & Skouras, JFE 2019; *Day destroys the night*, 2024 WP | US stocks, cross-section | Clientele: momentum earns overnight, other anomalies earn intraday | Cross-sectional; not applicable to one future |
| Hasbrouck, 2003 (*Intraday price formation*) | S&P 500 and **Nasdaq-100**: ETF, E-mini, big contract | E-mini dominates S&P price discovery (~90%), but **for the Nasdaq-100 the ETF (QQQ) led, with ~60%** | **NQ is not necessarily the RTH price leader**, so ES-based price-discovery findings may not transfer |
| *Information shares for markets with partially overlapping trading hours*, JBF 2023 | S&P 500 and Nasdaq-100 ETFs and E-minis | Conventional measures **overstate** ETF information shares once off-hours futures trading is counted | Supports measuring overnight price discovery in the future itself |
| Lockwood & McInish, JBF 1990 | US cash index | Variance higher intraday in both bull and bear markets; regime differences in means occur intraday | Benchmark for the stability analysis |
| Knuteson, 2016–2022 (arXiv essays) | Global indices | Asserts the overnight/intraday pattern is "suspicious" | Not peer-reviewed advocacy; recorded, not weighted |
| CME price-limit rules | ES/NQ/MNQ | Overnight limits **±5% until Oct 12 2020, then ±7% plus a 3.5% dynamic circuit breaker** | **Overnight tails are mechanically censored.** Built into the protocol. |

### 4a. Added 2026-11-11 for the price-discovery measure (P1). Read at abstract or excerpt level only; no numbers reproduced.

| Paper | Read | Relevance |
|---|---|---|
| Barclay & Warner, JFE 34 (1993) 281–305, *Stealth trading and volatility* | Abstract plus secondary descriptions | Introduced the weighted price contribution (WPC), comparing a group's share of cumulative price change with its share of trades and volume. This is the benchmark logic of P1-V. |
| Barclay & Hendershott, RFS 16(4) (2003) 1041–1073, *Price discovery and trading after hours* | Abstract plus opening pages | More information is revealed per hour during the trading day. Low after-hours volume still generates significant, if inefficient, price discovery. Nasdaq stocks, not futures. |
| Wang & Yang, JEDC 55 (2015), *How well does the weighted price contribution measure price discovery?* | Abstract | Examines WPC accuracy, including for overnight vs daytime returns. A recorded limitation of P1. |

## 5. Refutation search (RESEARCH_PROTOCOL.md rule), recorded even where it found nothing

| Search terms | Result |
|---|---|
| Boyarchenko Larsen Whelan later work, post-publication | **Found:** Liberty Street July 2026, drift gone in 2021–25, NQ included |
| Bondarenko Muravyev later work / replication | Nothing by the authors; Boyarchenko 2026 covers the adjacent window |
| Riedel Wagner replication / tail index overnight futures | Nothing direct found |
| Liu Tse follow-up / overnight futures post-2014 | Nothing direct; Lachance 2021 qualifies the ETF part |
| Overnight premium disappeared / recent evidence | Boyarchenko 2026; an April 2025 working paper attributing the gap to retail trading share (stocks, not futures) |
| Overnight price discovery Nasdaq-100 futures | Hasbrouck 2003; JBF 2023; a "Daytime vs overnight trading in equity index futures" paper on ES and NQ information shares (**full text not reachable**) |

## 6. What the literature supports, and what it does not

| Claim | Literature support | Transfers to NQ? | Status on this data |
|---|---|---|---|
| RTH variance per hour > overnight variance per hour | Unanimous, across decades and markets | Very likely | Near-certain; **a replication check, not a discovery** |
| Overnight return innovations are fatter-tailed after volatility scaling | Riedel & Wagner (cash indexes, non-trading nights) | **Uncertain**: Globex trades overnight | **Open: primary question** |
| A material share of daily price discovery happens overnight | Bondarenko & Muravyev (ES); JBF 2023 | Plausible, and NQ overnight liquidity has grown a lot since 2018 | **Open: primary question** |
| Large moves happen disproportionately overnight | Indirect (news timing, foreign shocks) | Plausible | **Open: primary question** |
| Overnight mean return > RTH mean return | Strong 1993–2020; **gone since 2021 per the original authors** | Weak | Underpowered (protocol §7); overlaps H3; descriptive only |
| Overnight return predicts RTH return | Liu & Tse; Branch & Ma | — | **Excluded:** this is H7 (rejected) by another name |

## Sources
- [Liu & Tse 2017, EconPapers](https://econpapers.repec.org/RePEc:eee:reveco:v:48:y:2017:i:c:p:440-451)
- [Bondarenko & Muravyev, JFQA abstract](https://cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/market-return-around-the-clock-a-puzzle/089E33AC0B4D3B9A02CBA31EDF6505B3) · [full working paper (NFA 2020)](https://portal.northernfinanceassociation.org/viewp.php?n=2240010836)
- [Riedel & Wagner, EconPapers](https://econpapers.repec.org/RePEc:eee:intfin:v:39:y:2015:i:c:p:53-64) · [SSRN 2494387](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2494387)
- [Boyarchenko et al., NY Fed SR 917](https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr917.pdf) · [The Disappearing Overnight Drift, July 2026](https://libertystreeteconomics.newyorkfed.org/2026/07/the-disappearing-overnight-drift/)
- [Lachance 2021, JFM](https://ideas.repec.org/a/eee/finmar/v52y2021ics138641812030032x.html)
- [Hasbrouck, Intraday price formation in US equity index markets](https://archive.nyu.edu/bitstream/2451/27374/2/FIN-00-046.pdf)
- [Information shares for markets with partially overlapping trading hours, JBF 2023](https://ideas.repec.org/a/eee/jbfina/v154y2023ics0378426623001681.html)
- [Lockwood & McInish 1990, JBF](https://econpapers.repec.org/RePEc:eee:jbfina:v:14:y:1990:i:6:p:1243-1253)
- [CME price-limit FAQ (Oct 12 2020 change)](https://www.cmegroup.com/trading/equity-index/faq-us-based-equity-index-price-limits.html.html)
- [Knuteson, arXiv 2010.01727](https://arxiv.org/abs/2010.01727v1)
