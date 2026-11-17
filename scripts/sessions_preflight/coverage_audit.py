# Coverage audit: bar COUNTS and VOLUME only. No price-derived statistic is computed here.
import sys, json, pandas as pd, numpy as np
f = sys.argv[1]
df = pd.read_csv(f, usecols=["timestamp","volume"])
ts = pd.to_datetime(df["timestamp"], utc=True)
out = {"file": f, "rows": len(df), "dup_ts": int(ts.duplicated().sum()),
       "monotonic": bool(ts.is_monotonic_increasing),
       "first_utc": str(ts.iloc[0]), "last_utc": str(ts.iloc[-1]),
       "zero_or_nan_volume": int((df["volume"].fillna(0)<=0).sum())}
et = ts.dt.tz_convert("America/New_York")
mins = et.dt.hour*60 + et.dt.minute
# CME session date: bars from 18:00 ET belong to next day's session
sess = (et + pd.Timedelta(hours=6)).dt.normalize().dt.tz_localize(None).dt.date
part = np.select([(mins>=570)&(mins<960), (mins>=960)&(mins<1020)], ["RTH","POST"], "ON")
d = pd.DataFrame({"sess":sess,"part":part,"mins":mins,"vol":df["volume"].values,"year":(et + pd.Timedelta(hours=6)).dt.year})
g = d.groupby(["sess","part"]).size().unstack(fill_value=0)
g["year"] = pd.to_datetime(pd.Series(g.index)).dt.year.values
# expected: RTH 390, ON 18:00->09:30 = 930 minus nothing (17:00-18:00 halt is outside)
full_rth = g["RTH"]>=390
out["sessions"] = int(len(g))
out["sessions_with_any_rth"] = int((g["RTH"]>0).sum())
out["sessions_rth_full_390"] = int(full_rth.sum())
out["sessions_rth_short_(1-389)"] = int(((g["RTH"]>0)&(g["RTH"]<390)).sum())
out["short_rth_sessions_list"] = [f"{k}:{v}" for k,v in g.loc[(g['RTH']>0)&(g['RTH']<390),'RTH'].items()][:80]
yr = g.groupby("year").agg(sessions=("RTH","size"), rth_bars_median=("RTH","median"), on_bars_median=("ON","median"),
                           on_bars_p10=("ON", lambda x: float(np.percentile(x,10))), on_min=("ON","min"))
yr["on_coverage_median_pct"] = (yr["on_bars_median"]/930*100).round(1)
yr["rth_coverage_median_pct"] = (yr["rth_bars_median"]/390*100).round(1)
out["by_year"] = yr.reset_index().to_dict(orient="records")
# per-hour coverage (fraction of sessions with a bar in each minute, averaged over hour), by year group
d["hour"] = d["mins"]//60
cov = d.groupby(["year","hour"]).size() / d.groupby("year")["sess"].nunique() / 60
out["hourly_minute_coverage_pct"] = (cov.unstack().round(3)*100).to_dict(orient="index")
vol = d.groupby(["year","part"])["vol"].median().unstack()
out["median_1min_volume_by_part"] = vol.round(1).to_dict(orient="index")
# largest intra-session gaps (minutes) excluding the 17:00-18:00 ET halt and weekends
dt = ts.diff().dt.total_seconds()/60
gap = pd.DataFrame({"et":et,"gap":dt})
gap = gap[(gap.gap>15)&(gap.gap<60*40)]
gap = gap[~((gap.et.dt.hour==18)&(gap.et.dt.minute<=15))]
out["gaps_over_15min_excl_daily_halt"] = int(len(gap))
out["gaps_sample"] = [f"{r.et} gap={int(r.gap)}m" for r in gap.sort_values("gap",ascending=False).head(25).itertuples()]
print(json.dumps(out, indent=1, default=str))
