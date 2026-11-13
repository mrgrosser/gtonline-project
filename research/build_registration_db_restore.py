#!/usr/bin/env python3
"""Generate guarded native PG7.3 recovery SQL; NEVER connects or executes it.
Original and expected-current snapshots must be verified before use. SQL locks
only the two relevant tables, checks current rows, restores IDs1/5/6 atomically,
and asserts exact equality before COMMIT. Use only with game stopped.
"""
import argparse,hashlib,json,os
from pathlib import Path
TABLES=('category5_object','category5_attr')
def verified(directory):
    manifest=json.loads((directory/'manifest.json').read_text());result={}
    for table in TABLES:
        raw=(directory/(table+'.sql')).read_bytes();m=manifest[table]
        if len(raw)!=m['bytes'] or hashlib.sha256(raw).hexdigest()!=m['sha256']:
            raise ValueError('Snapshot integrity failure')
        if m['rows']!={'category5_object':3,'category5_attr':15}[table]:
            raise ValueError('Unexpected snapshot scope')
        text=raw.decode()
        if not text.startswith('INSERT INTO '+table+' ('):raise ValueError('Snapshot format')
        result[table]=text
    return result

def substitute(sql,source,target):return sql.replace('INSERT INTO '+source+' (','INSERT INTO '+target+' (')
def equal(a,b):
    return "SELECT 1 / CASE WHEN count(*)=0 THEN 1 ELSE 0 END FROM ((SELECT * FROM %s EXCEPT SELECT * FROM %s) UNION ALL (SELECT * FROM %s EXCEPT SELECT * FROM %s)) AS differences;"%(a,b,b,a)
def build(original,current):
    out=['\\set ON_ERROR_STOP on','BEGIN;',
         'LOCK TABLE public.category5_object,public.category5_attr IN SHARE ROW EXCLUSIVE MODE;']
    for i,t in enumerate(TABLES):
        for tag,data in [('original',original),('current',current)]:
            name='gt_restore_'+tag+'_'+str(i)
            out += ['CREATE TEMP TABLE '+name+' AS SELECT * FROM public.'+t+' WHERE 1=0;',substitute(data[t],t,name)]
        out += ['CREATE TEMP TABLE gt_restore_live_'+str(i)+' AS SELECT * FROM public.'+t+' WHERE object_id IN (1,5,6);',
                equal('gt_restore_live_'+str(i),'gt_restore_current_'+str(i))]
    out += ['DELETE FROM public.category5_attr WHERE object_id IN (1,5,6);',
            'DELETE FROM public.category5_object WHERE object_id IN (1,5,6);']
    for t in TABLES:out.append(substitute(original[t],t,'public.'+t))
    for i,t in enumerate(TABLES):
        out += ['CREATE TEMP TABLE gt_restore_after_'+str(i)+' AS SELECT * FROM public.'+t+' WHERE object_id IN (1,5,6);',
                equal('gt_restore_after_'+str(i),'gt_restore_original_'+str(i))]
    out += ['COMMIT;']
    return '\n'.join(out)+'\n'
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('original',type=Path);p.add_argument('current',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    data=build(verified(a.original),verified(a.current))
    fd=os.open(str(a.output),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as f:f.write(data)
    print('Guarded SQL generated privately; NOT executed')
