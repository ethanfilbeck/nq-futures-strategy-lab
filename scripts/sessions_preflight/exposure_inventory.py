# Exposure inventory. Reads ONLY 'timestamp' columns. Reconstructs which session dates entered earlier
# H8 / placebo / replication computations, using the same day and window logic as nq_bot/family3.py,
# run_h8_placebo.py and run_h8_{es,m2k}_replication.py / run_h8_gold_control.py.
import os, json, pandas as pd, numpy as np
R=os.path.expanduser('~/mnt/nq_bot')
FOMC=["2019-06-19","2019-07-31","2019-09-18","2019-10-30","2019-12-11","2020-01-29","2020-04-29","2020-06-10","2020-07-29","2020-09-16","2020-11-05","2020-12-16","2021-01-27","2021-03-17","2021-04-28","2021-06-16","2021-07-28","2021-09-22","2021-11-03","2021-12-15","2022-01-26","2022-03-16","2022-05-04","2022-06-15","2022-07-27","2022-09-21","2022-11-02","2022-12-14","2023-02-01","2023-03-22","2023-05-03","2023-06-14","2023-07-26","2023-09-20","2023-11-01","2023-12-13","2024-01-31","2024-03-20","2024-05-01","2024-06-12","2024-07-31","2024-09-18","2024-11-07","2024-12-18","2025-01-29","2025-03-19","2025-05-07","2025-06-18"]
HO=["2025-07-30","2025-09-17","2025-10-29","2025-12-10","2026-01-28","2026-03-18","2026-04-29","2026-06-17","2026-07-29","2026-09-16","2026-10-28"]
REAL=[pd.Timestamp(x).date() for x in FOMC+HO]; REALS=set(REAL)
def cal(files):
    ts=pd.concat([pd.read_csv(f'{R}/data/{f}',usecols=['timestamp'])['timestamp'] for f in files])
    ts=pd.to_datetime(ts,utc=True).drop_duplicates().sort_values()
    et=ts.dt.tz_convert('America/New_York'); m=et.dt.hour*60+et.dt.minute; d=et.dt.date
    rth=(m>=570)&(m<960)&(et.dt.weekday<5)
    cnt=d[rth].value_counts()
    days=sorted([x for x,n in cnt.items() if n>=300])
    h14=set(d[m==840]); h1355=set(d[m==835])
    return days,h14,h1355
def windows(days,h14,h1355,pairs):
    return [(p,e) for p,e in pairs if p in h14 and e in h1355]
out={}
for mk,files in {'MNQ':['mnq_train.csv','mnq_holdout.csv'],'MES':['mes_2019_2026.csv'],'M2K':['m2k_2019_2026.csv'],'MGC':['mgc_2019_2026.csv']}.items():
    days,h14,h1355=cal(files); idx={d:i for i,d in enumerate(days)}
    cons=[(days[i],days[i+1]) for i in range(len(days)-1)]
    real=windows(days,h14,h1355,[(days[idx[e]-1],e) for e in REAL if e in idx and idx[e]>0])
    rec={'real':real}
    if mk in ('MES','M2K','MGC'):
        rec['repl_pool']=windows(days,h14,h1355,[(p,e) for p,e in cons if p not in REALS and e not in REALS])
    if mk in ('MNQ','MES','M2K'):
        ban=set()
        for e in REAL:
            if e in idx:
                for j in range(idx[e]-3,idx[e]+4):
                    if 0<=j<len(days): ban.add(days[j])
        sh=[]
        for off in (-21,-14,-7,7,14,21):
            for e in REAL:
                d=(pd.Timestamp(e)+pd.Timedelta(days=off)).date()
                if d in ban or d not in idx or idx[d]==0: continue
                sh.append((days[idx[d]-1],d,off))
        rec['sham']=[(p,e) for p,e,o in sh if p in h14 and e in h1355]
        rec['wed_pool']=windows(days,h14,h1355,[(p,e) for p,e in cons if p not in ban and e not in ban and e.weekday()==2])
    out[mk]=rec
pickle=__import__('pickle'); pickle.dump(out,open(os.path.expanduser('~/scratch/exposure.pkl'),'wb'))
a,b=pd.Timestamp('2025-07-01').date(),pd.Timestamp('2026-10-30').date()
for mk,rec in out.items():
    print(mk,{k:(len(v),sum(1 for p,e in v if a<=e<=b)) for k,v in rec.items()})
