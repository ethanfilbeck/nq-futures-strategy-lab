import os, json, pandas as pd
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'verify_counts_and_rolls.py')).read().split('# rolls')[0])
rm=json.load(open(f'{R}/runs/rollmap_MNQ.json')); roll=set(pd.Timestamp(p['from']) for p in rm['periods'][1:])
north=pd.to_datetime(['2021-04-02','2023-04-07','2025-01-09','2026-04-03']); after={g.index[g.index>d][0]:d for d in north}
DEV=["2020-01-29","2020-04-29","2020-06-10","2020-07-29","2020-09-16","2020-11-05","2020-12-16","2021-01-27","2021-03-17","2021-04-28","2021-06-16","2021-07-28","2021-09-22","2021-11-03","2021-12-15","2022-01-26","2022-03-16","2022-05-04","2022-06-15","2022-07-27","2022-09-21","2022-11-02","2022-12-14","2023-02-01","2023-03-22","2023-05-03","2023-06-14","2023-07-26","2023-09-20","2023-11-01","2023-12-13","2024-01-31","2024-03-20","2024-05-01","2024-06-12","2024-07-31","2024-09-18","2024-11-07","2024-12-18","2025-01-29","2025-03-19","2025-05-07","2025-06-18"]
HO=["2025-07-30","2025-09-17","2025-10-29","2025-12-10","2026-01-28","2026-03-18","2026-04-29","2026-06-17","2026-07-29","2026-09-16","2026-10-28"]
def fomc_set(lst):
    s={}
    for e in lst:
        e=pd.Timestamp(e); s[e]='statement day'; s[g.loc[e,'prev']]='day before'
    return s
F=fomc_set(DEV+HO)
def rules(d,r):
    return {'E1':bool(r.early),'E2':bool(r.prev_early),'E3':not(r.has_open and r.has_close and r.prev_has_close),
            'E4':d in roll,'E5':d in after,'E6':d in F}
for name,a,b in [('DEV','2020-01-02','2025-06-30'),('HOLDOUT','2025-07-01','2026-10-30')]:
    x=g[(g.index>=a)&(g.index<=b)]
    tab=pd.DataFrame({d:rules(d,r) for d,r in x.iterrows()}).T
    print(f'\n== {name}: sessions with >=1 RTH bar = {len(x)}; full 390-bar = {int((x.n>=390).sum())}; '
          f'non-early sessions with <390 bars = {int(((x.n<390)&~x.early).sum())} {[str(d.date()) for d in x.index[(x.n<390)&~x.early]]}')
    print('standalone hits per rule:', tab.sum().astype(int).to_dict())
    rem=pd.Series(True,index=tab.index); seq={}
    for k in ['E1','E2','E3','E4','E5','E6']:
        hit=rem&tab[k]; seq[k]=int(hit.sum()); rem&=~tab[k]
        print(f'  sequential {k}: -{seq[k]:4d} -> {int(rem.sum())}')
    # overlaps
    for k in ['E4','E5','E6']:
        ov=tab[tab[k]&tab.drop(columns=k).any(axis=1)]
        print(f'  {k} sessions also hit by another rule:', {str(d.date()):[c for c in tab.columns if c!=k and ov.loc[d,c]] for d in ov.index})
    print('  E6 sessions in window:', len([d for d in F if a<=str(d.date())<=b]))
print('\nFOMC exclusion list (both periods):')
for d in sorted(F): 
    if '2020-01-02'<=str(d.date())<='2026-10-30': print(' ',d.date(),d.day_name()[:3],F[d])
# no-RTH sessions
ts=pd.to_datetime(pd.concat([pd.read_csv(f'{R}/data/{f}',usecols=['timestamp'])['timestamp'] for f in ['mnq_train.csv','mnq_holdout.csv']]),utc=True)
et=ts.dt.tz_convert('America/New_York'); sd=(et+pd.Timedelta(hours=6)).dt.date
print('\nNo-RTH sessions:')
for d in north:
    m=et[sd==d.date()]
    print(f'  session {d.date()} ({d.day_name()}): {len(m)} bars, first {m.min()}, last {m.max()}; next RTH session {[k for k,v in after.items() if v==d][0].date()}; prev RTH session {g.index[g.index<d][-1].date()}')
