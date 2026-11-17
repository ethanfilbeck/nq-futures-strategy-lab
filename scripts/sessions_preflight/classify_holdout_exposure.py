import os, pickle, json, pandas as pd
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'verify_counts_and_rolls.py')).read().split('# rolls')[0])  # session table g (timestamps only)
ex=pickle.load(open(os.path.expanduser('~/scratch/exposure.pkl'),'rb'))
def sess_of(wins): 
    s={}
    for p,e in wins: s.setdefault(pd.Timestamp(p),[]).append('d-'); s.setdefault(pd.Timestamp(e),[]).append('d')
    return s
tags={}
for mk,rec in ex.items():
    for k,w in rec.items():
        for d,roles in sess_of(w).items():
            tags.setdefault(d,set()).add(f'{mk}:{k}')
# eligibility (E1-E5) recomputed as in verify.py
import json as J
rm=J.load(open(f'{R}/runs/rollmap_MNQ.json')); roll=set(pd.Timestamp(p['from']) for p in rm['periods'][1:])
north=pd.to_datetime(['2021-04-02','2023-04-07','2025-01-09','2026-04-03']); after=set(g.index[g.index>d][0] for d in north)
rows=[]
for d,r in g[(g.index>='2025-07-01')&(g.index<='2026-10-30')].iterrows():
    rule = 'E1' if r.early else 'E2' if r.prev_early else 'E3' if not(r.has_open and r.has_close and r.prev_has_close) else 'E4' if d in roll else 'E5' if d in after else ''
    t=tags.get(d,set())
    cat = 'A_H8' if any(x.endswith(':real') for x in t) else 'P_placebo' if any(x.endswith((':sham',':wed_pool')) for x in t) else 'B_replication_pool' if any(x.endswith(':repl_pool') for x in t) else 'U_unexposed'
    rows.append(dict(session=str(d.date()),weekday=d.day_name()[:3],excluded_by=rule,category=cat,tests=';'.join(sorted(t))))
df=pd.DataFrame(rows)
df.to_csv('docs/HOLDOUT_EXPOSURE_SESSIONS.csv',index=False)
print('all holdout sessions with RTH:',len(df)); print(pd.crosstab(df.category,df.excluded_by.replace('', 'eligible'),margins=True))
el=df[df.excluded_by=='']
print('\neligible by category x weekday'); print(pd.crosstab(el.category,el.weekday,margins=True))
print('\nU_unexposed eligible sessions:',el[el.category=='U_unexposed'].session.tolist())
print('\nA_H8:',df[df.category=='A_H8'][['session','weekday','excluded_by','tests']].to_string(index=False))
# exposure ignoring the replication pool (B): sessions with no MNQ exposure and no event/sham/Wed exposure
print('\nP placebo eligible by source: MNQ-involved', int(el[(el.category=='P_placebo')&el.tests.str.contains('MNQ:')].shape[0]))
