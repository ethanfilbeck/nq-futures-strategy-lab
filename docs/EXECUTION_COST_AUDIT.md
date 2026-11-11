# Execution-cost audit: is 1 tick of slippage realistic?

Run 2026-11-11, the third of three research checkpoints. Simulation only.

**Conclusion: the 1-tick assumption is sound for the spread, optimistic about timing, and — most
importantly — not load-bearing for any conclusion this project has reached.**

## What the model assumes

Market entries and exits fill **1 tick against us** (MNQ tick = 0.25 points = **$0.50** per side, so **$1.00**
per round turn), plus $0.62 per side commission. Signals computed at a bar's close are filled at the **next**
bar's open, so a full bar of latency is already built in.

## Evidence quality

**No stored fill records exist.** The 13 IB paper drills ran live against TWS and their journal output is not
retained in the repository, so actual-versus-modelled fill prices cannot be compared. The one hard datum from
them is commission: **$0.61/side observed against $0.62 assumed**, i.e. the commission model is slightly
conservative and correct.

Everything below is therefore a **proxy analysis from 1-minute OHLCV**, labelled as such. A direct test would
need either the drill journals or quote data, neither of which is available.

## Liquidity at each strategy's actual entry minute

| Strategy | n | Entry hour | Median volume | 10th pct volume | Median bar range | 1 tick as % of range |
|---|---|---|---|---|---|---|
| ORB | 1,602 | 09:00 | 3,812 | 1,063 | 54 ticks | 1.9% |
| H1 / H2 | 1,277 | 15:00 | 1,513 | 521 | 36 ticks | 2.8% |
| H3 overnight drift | 1,576 | **02:00** | **352** | **102** | 23 ticks | 4.3% |
| H4 liquidity sweep | 288 | 10:00 | 2,813 | 630 | 47 ticks | 2.1% |
| H5 VWAP pullback | 1,399 | 10:00 | 2,417 | 770 | 45 ticks | 2.2% |
| H6 turn of month | 73 | 15:00 | 4,682 | 1,098 | 61 ticks | 1.6% |
| H7 gap reversal | 439 | 09:00 | 6,688 | 1,711 | 91 ticks | 1.1% |
| **H8 pre-FOMC** | 48 | **14:00** | **1,075** | 352 | 31 ticks | 3.2% |
| H9 / H10 | 141 / 59 | 15:00 | ~4,900 | ~1,350 | ~58 ticks | 1.7% |
| H11 opening hour | 253 | 10:00 | 3,828 | 858 | 70 ticks | 1.4% |

**Depth is not the constraint.** Even H3, the thinnest, trades a median 352 contracts in its entry minute
and 102 at the 10th percentile, against an order of **one** contract. No strategy here could move the market.

**Two findings worth separating:**

1. **1 tick is a fair model of the spread.** MNQ quotes 1 tick wide through all the hours these strategies
   trade. A one-lot market order crosses the spread and fills at the touch — which is exactly 1 tick. For
   this component the assumption is right, not optimistic.
2. **It is optimistic about timing.** The model fills at the *bar's open*, a reference print. Entry minutes
   span 23–91 ticks of range, so 1 tick is only 1–4% of the distance price travels within that minute.
   Arriving a few seconds late costs far more than the spread. This matters least for the clock-driven
   strategies, where the entry time is known in advance and an order can be positioned at the touch
   (H8's dates are known *months* ahead), and most for strategies reacting to a condition.

For reference, liquidity by hour across the whole sample: 02:00 ET median volume 158, 09:00 1,229, 10:00
2,440, 14:00 1,067, 18:00 103. H3 is the one strategy entering in genuinely thin conditions.

## Does the assumption change any conclusion? No.

Each extra tick costs $1.00 per round turn. Testing every event strategy against its own pre-registered bar:

| Strategy | Bar | t at modelled cost | +1 tick | +3 ticks | Verdict changes? |
|---|---|---|---|---|---|
| H6 turn of month | 3.0 | 0.45 | 0.44 | 0.41 | no |
| H7 gap reversal | 3.0 | −0.74 | −0.82 | −1.00 | no |
| H8 pre-FOMC | 3.0 | 3.02 | 3.00 | 2.96 | only at 4× slippage |
| H9 macro days | 3.5 | 0.23 | 0.21 | 0.15 | no |
| H10 pre-holiday | 3.5 | 1.70 | 1.68 | 1.63 | no |
| H11 opening hour | 3.5 | 0.36 | 0.31 | 0.22 | no |

H8 in detail, across the slippage ladder:

| Extra ticks | As published | Roll-adjusted |
|---|---|---|
| 0 | t 3.02, $148.23/trade | t 2.63, $124.10 |
| 1 | t 3.00, $147.23 | t 2.61, $123.10 |
| 2 | t 2.98, $146.23 | t 2.58, $122.10 |
| 4 | t 2.94, $144.23 | t 2.54, $120.10 |

**H8 is essentially insensitive to execution cost.** Quintupling slippage moves its t-statistic by 0.08.
Its per-trade edge is ~$148 against $1.00 per extra tick. **H8's problems are contract rolls and sample
size, not execution** — and the roll correction moved it ten times further than 4× slippage does.

The intraday failures are equally insensitive in the other direction: the cross-strategy post-mortem
established that **eleven of twelve fail at literally zero cost**, so additional slippage only deepens a
failure that already exists. At 2 ticks: H1 −$6,059 → −$7,336, H2 −$2,611 → −$3,888, H3 −$576 → −$2,009,
H5 −$2,336 → −$3,504, H4 +$1,204 → +$962.

## Limitations

- **Proxy, not measurement.** Bar volume and range stand in for the spread and for fill quality because no
  quote data and no stored fill records exist.
- **H3 is the weakest case.** Entering at 02:00 ET in a 352-contract minute, the spread may genuinely exceed
  1 tick on some days. H3 failed anyway, and fails harder at 2 ticks (−$2,009), so nothing rests on it.
- **Partial fills and queue position are not modelled.** For one contract this is reasonable; for size it
  would not be, and nothing here supports trading size.
- **The forward paper test will settle this properly.** IB returns actual fill prices, so after a handful of
  live events the modelled and realised slippage can be compared directly. That is the right way to close
  this question, and it costs nothing.

## Recommendation

Keep the 1-tick model, keep reporting every result at 2 ticks as the pre-registrations already require, and
**measure realised slippage from the forward paper fills** rather than arguing about it from bar data. No
change to any strategy rule follows from this audit.
