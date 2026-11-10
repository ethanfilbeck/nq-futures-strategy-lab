"""The single pre-registered holdout run for H8 (docs/PREREG_FAMILY3_HOLDOUT.md). Run once."""
import json
import sys
from pathlib import Path

from nq_bot import family3 as f3
from nq_bot.data import load_csv

TRAIN_RANDOM_LONG_MEAN = 9.51   # from runs/family3_results.json (H8 benchmark_mean_per_trade), frozen beforehand

bars = load_csv(sys.argv[1] if len(sys.argv) > 1 else "data/mnq_holdout.csv")
s = f3.Session(bars)
trades, skipped = f3.run_h8(s, f3.HOLDOUT_FOMC_DAYS)
st = f3.stats(trades)
fail = st["n"] == 0 or st["net"] <= 0 or st["mean"] <= TRAIN_RANDOM_LONG_MEAN
out = {"data": [str(bars.index[0]), str(bars.index[-1])], "skipped": skipped, "stats": st,
       "trades": [{"entry": str(t.entry_ts), "exit": str(t.exit_ts), "entry_px": t.entry, "exit_px": t.exit,
                   "kind": t.kind, "net": round(t.net(), 2)} for t in trades],
       "verdict": "HOLDOUT FAIL" if fail else "HOLDOUT CONSISTENT (not proof)"}
Path("runs").mkdir(exist_ok=True)
Path("runs/family3_holdout.json").write_text(json.dumps(out, indent=2))
for t in out["trades"]:
    print(f"{t['entry'][:16]} -> {t['exit'][:16]}  {t['entry_px']:>9.2f} -> {t['exit_px']:>9.2f}  {t['kind']:5s} ${t['net']:>8.2f}")
print(f"n={st['n']} net=${st.get('net', 0):,.2f} mean=${st.get('mean', 0):.2f} skipped={skipped} -> {out['verdict']}")
