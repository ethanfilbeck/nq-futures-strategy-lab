import os, json, pandas as pd, numpy as np
exec(open('scripts/sessions_preflight/verify_counts_and_rolls.py').read().split('# rolls')[0])
c=pd.read_csv('docs/HOLDOUT_EXPOSURE_SESSIONS.csv',keep_default_na=False)
o2=pd.DatetimeIndex(pd.to_datetime(c[(c.excluded_by=='')&(c.category=='B_replication_pool')].session))
prev=pd.DatetimeIndex(pd.to_datetime(g.loc[o2,'prev'].values))
gap=np.asarray((o2-prev).days)
v1=np.isin(o2.dayofweek,[1,2,3,4])&(gap==1)
print('O2 n',len(o2),'O2 V1 (Tue-Fri non-long):',int(v1.sum()),'long overnights:',int((gap>1).sum()), pd.Series(o2[v1].day_name().str[:3]).value_counts().to_dict())
north=pd.to_datetime(['2021-04-02','2023-04-07','2025-01-09','2026-04-03']); after=set(g.index[g.index>x][0] for x in north)
rm=json.load(open('runs/rollmap_MNQ.json')); roll=set(pd.Timestamp(p['from']) for p in rm['periods'][1:])
import re
FO=re.findall(r'"(20\d\d-\d\d-\d\d)"',open('nq_bot/family3.py').read().split('FOMC_DAYS = [')[1].split(']')[0])
F=set()
for e in FO:
    e=pd.Timestamp(e)
    if e in g.index: F|={e,pd.Timestamp(g.loc[e,'prev'])}
x=g[(g.index>='2020-01-02')&(g.index<='2025-06-30')]
el=pd.DatetimeIndex([s for s,r in x.iterrows() if not(r.early or r.prev_early or not(r.has_open and r.has_close and r.prev_has_close) or s in roll or s in after or s in F)])
print('dev primary',len(el))
mt=el[np.isin(el.dayofweek,[0,3,4])]
print('dev matched Mon/Thu/Fri',len(mt),pd.Series(mt.day_name().str[:3]).value_counts().to_dict())
gp=np.asarray((el-pd.DatetimeIndex(pd.to_datetime(g.loc[el,'prev'].values))).days)
print('dev matched V1 Thu/Fri non-long:',int((np.isin(el.dayofweek,[3,4])&(gp==1)).sum()), ' (plus Tue non-long dev:',int((np.isin(el.dayofweek,[1])&(gp==1)).sum()),')')
