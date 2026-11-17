# Verification for the sessions pre-registration. Reads ONLY the 'timestamp' column of each file.
# No open/high/low/close/volume value is loaded, so no return or volatility can be computed here.
import json, hashlib, datetime as dt, pandas as pd, numpy as np
B='/'.join(__file__.split('/')[:0])
import os; R=os.path.expanduser('~/mnt/nq_bot')
cols=pd.read_csv(f'{R}/data/mnq_train.csv',nrows=0).columns.tolist()
ts=pd.concat([pd.read_csv(f'{R}/data/{f}',usecols=['timestamp'])['timestamp'] for f in ['mnq_train.csv','mnq_holdout.csv']])
ts=pd.to_datetime(ts,utc=True); assert ts.is_monotonic_increasing and not ts.duplicated().any()
et=ts.dt.tz_convert('America/New_York'); m=(et.dt.hour*60+et.dt.minute).values
sess=(et+pd.Timedelta(hours=6)).dt.date.values
df=pd.DataFrame({'s':sess,'m':m})
rth=df[(df.m>=570)&(df.m<960)]
g=rth.groupby('s').agg(n=('m','size'),last=('m','max'),first=('m','min'))
g['has_open']=rth[(rth.m<575)].groupby('s').size().reindex(g.index).fillna(0)>0
g['has_close']=rth[(rth.m>=955)].groupby('s').size().reindex(g.index).fillna(0)>0
g['early']=g['last']<=795
g.index=pd.to_datetime(g.index)
sessions=g.index
g['prev']=pd.Series(sessions,index=sessions).shift(1)
g['prev_early']=g['early'].shift(1).fillna(True).astype(bool)
g['prev_has_close']=g['has_close'].shift(1).fillna(False).astype(bool)
# rolls
rm=json.load(open(f'{R}/runs/rollmap_MNQ.json'))
per=rm['periods']; sw=[]
mcode={'H':3,'M':6,'U':9,'Z':12}
def third_friday(y,mo):
    d=dt.date(y,mo,15); 
    while d.weekday()!=4: d+=dt.timedelta(1)
    return d
rows=[]
for a,b in zip(per[:-1],per[1:]):
    T=pd.Timestamp(b['from'],tz='UTC'); Tet=T.tz_convert('America/New_York')
    old=a['contract']; new=b['contract']
    yo=int(old[-1]); base=(T.year//10)*10; y=base+yo
    if y< T.year-1: y+=10
    exp=third_friday(y,mcode[old[3]])
    # session d containing T in its overnight: first session date > Tet date with 16:00 prev < T <= 09:30 d
    cand=[d for d in sessions if (pd.Timestamp(d).tz_localize('America/New_York')+pd.Timedelta(hours=9,minutes=30))>=Tet]
    d=cand[0]; dprev=g.loc[d,'prev']
    cprev=pd.Timestamp(dprev).tz_localize('America/New_York')+pd.Timedelta(hours=16)
    inside= cprev < Tet <= pd.Timestamp(d).tz_localize('America/New_York')+pd.Timedelta(hours=9,minutes=30)
    near=int(((ts>=T-pd.Timedelta(minutes=30))&(ts<=T+pd.Timedelta(minutes=30))).sum())
    order_ok = ('HMUZ'.index(new[3])==('HMUZ'.index(old[3])+1)%4)
    rows.append(dict(switch_utc=str(T), switch_et=Tet.strftime('%a %Y-%m-%d %H:%M %Z'), old=old,new=new,
        old_expiry=str(exp), days_before_expiry=(exp-T.date()).days, consecutive=order_ok,
        session=str(d.date()), in_overnight=bool(inside), bars_pm30min=near))
rolls=pd.DataFrame(rows)
roll_sess=set(pd.to_datetime(rolls.session))
# FOMC
dev_fomc=["2020-01-29","2020-04-29","2020-06-10","2020-07-29","2020-09-16","2020-11-05","2020-12-16","2021-01-27","2021-03-17","2021-04-28","2021-06-16","2021-07-28","2021-09-22","2021-11-03","2021-12-15","2022-01-26","2022-03-16","2022-05-04","2022-06-15","2022-07-27","2022-09-21","2022-11-02","2022-12-14","2023-02-01","2023-03-22","2023-05-03","2023-06-14","2023-07-26","2023-09-20","2023-11-01","2023-12-13","2024-01-31","2024-03-20","2024-05-01","2024-06-12","2024-07-31","2024-09-18","2024-11-07","2024-12-18","2025-01-29","2025-03-19","2025-05-07","2025-06-18"]
ho_fomc=["2025-07-30","2025-09-17","2025-10-29","2025-12-10","2026-01-28","2026-03-18","2026-04-29","2026-06-17","2026-07-29","2026-09-16","2026-10-28"]
def pairs(lst):
    out=[]
    for e in lst:
        e=pd.Timestamp(e); assert e in sessions, e
        out.append((g.loc[e,'prev'],e))
    return out
ho_pairs=pairs(ho_fomc); dev_pairs=pairs(dev_fomc)
fomc_sess=lambda P: set([p for p,_ in P]+[e for _,e in P])
def count(a,b,extra=set()):
    x=g[(g.index>=a)&(g.index<=b)].copy()
    r={'sessions_with_rth':len(x),'full_390':int((x.n>=390).sum())}
    x['ex_early']=x.early; x['ex_prev_early']=~x.early & x.prev_early
    x['ex_noopen']=~x.early&~x.prev_early&(~x.has_open|~x.has_close|~x.prev_has_close)
    base=~x.early&~x.prev_early&x.has_open&x.has_close&x.prev_has_close
    x['ex_roll']=base & x.index.isin(roll_sess)
    elig=base&~x.index.isin(roll_sess)
    r.update(excl_early_close=int(x.ex_early.sum()),excl_prev_early=int(x.ex_prev_early.sum()),
      excl_missing_boundary=int(x.ex_noopen.sum()),excl_roll=int(x.ex_roll.sum()),eligible=int(elig.sum()))
    r['eligible_monday_or_long']=int((elig&((x.index-x.prev).dt.days>1)).sum())
    if extra:
        r['fomc_tierA_in_eligible']=int((elig&x.index.isin(extra)).sum())
        r['eligible_excl_fomc']=int((elig&~x.index.isin(extra)).sum())
    return r, x[elig].index
dev,dev_idx=count('2020-01-02','2025-06-30',fomc_sess(dev_pairs))
ho,ho_idx=count('2025-07-01','2026-10-30',fomc_sess(ho_pairs))
y19,_=count('2019-05-07','2019-12-31')
print('COLUMNS IN FILE (not loaded except timestamp):',cols)
print(json.dumps({'dev':dev,'holdout':ho,'2019':y19},indent=1))
print(rolls.to_string())
print('holdout H8 tier-A session pairs:',[(str(p.date()),pd.Timestamp(p).day_name()[:3],str(e.date()),e.day_name()[:3]) for p,e in ho_pairs])
print('tierA sessions overlapping roll sessions:',sorted(str(s.date()) for s in fomc_sess(ho_pairs)&roll_sess), sorted(str(s.date()) for s in fomc_sess(dev_pairs)&roll_sess))
# where do excluded-by-other-rules tierA land
print('tierA holdout sessions NOT in eligible set:',sorted(str(s.date()) for s in fomc_sess(ho_pairs) if s not in set(ho_idx)))
# Tier B: all Tuesday->Wednesday hold windows in holdout entered the pooled placebo calc; sham Wednesdays
wed=[d for d in ho_idx if d.dayofweek==2]; print('holdout eligible Wednesdays',len(wed))
for s in sorted(roll_sess):
    if pd.Timestamp('2020-01-02')<=s<=pd.Timestamp('2026-10-30'):
        r=g.loc[s]; 
        if r.early or r.prev_early: print('roll session also excluded by another rule:',s.date(),'early',r.early,'prev_early',r.prev_early,'prev',r.prev.date())
x=g[(g.index>='2020-01-02')&(g.index<='2025-06-30')]
print('dev sessions with Globex bars but no RTH bars:', sorted(set(pd.to_datetime(pd.Series(df.s.unique())))-set(g.index)) [ :0] )
allsess=set(pd.to_datetime(pd.Series(df.s.unique())))
print('no-RTH sessions 2019-2026:',sorted(str(d.date()) for d in allsess-set(g.index)))
north=pd.to_datetime(['2021-04-02','2023-04-07','2025-01-09','2026-04-03'])
after=[g.index[g.index>d][0] for d in north]
print('sessions whose overnight spans a no-RTH session:',[str(a.date()) for a in after])
for name,(a,b,idx,F) in {'dev':('2020-01-02','2025-06-30',dev_idx,fomc_sess(dev_pairs)),'holdout':('2025-07-01','2026-10-30',ho_idx,fomc_sess(ho_pairs))}.items():
    e=set(idx)-set(after); print(name,'eligible',len(e),'excl spans-no-RTH',len(set(idx)&set(after)),'eligible excl FOMC tierA',len(e-F),'tierA in eligible',len(e&F), 'Tue-Fri non-long', sum(1 for d in e if d.dayofweek in (1,2,3,4) and (d-g.loc[d,'prev']).days==1), 'Tue-Fri non-long excl FOMC', sum(1 for d in e-F if d.dayofweek in (1,2,3,4) and (d-g.loc[d,'prev']).days==1))
