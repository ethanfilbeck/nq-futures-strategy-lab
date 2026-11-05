import json, sys
from nq_bot.backtest import walk_forward
from nq_bot.config import load_settings, override
from nq_bot.data import load_csv
from research_edge import RESEARCH
cfg = override(load_settings("config/settings.yaml"), RESEARCH)
bars = load_csv("data/mnq_train.csv")
grid = {"strategy.opening_range_minutes": [15, 30], "strategy.reward_risk": [1.5, 2.0],
        "strategy.max_stop_atr": [1.0, 1.5]}
res = walk_forward(bars, cfg, grid, n_folds=5)
for f in res["folds"]:
    print(json.dumps({k: f.get(k) for k in ("fold","train_end","test_end","params")}),
          json.dumps({k: f["oos"].get(k) for k in ("trades","net_profit","profit_factor","win_rate_pct")}) if f.get("oos") else "")
print("OOS:", json.dumps(res["oos_summary"], indent=1))
res["oos_trades"].to_csv("runs/wf_oos_trades.csv", index=False)
