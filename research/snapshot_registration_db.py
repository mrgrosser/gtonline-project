#!/usr/bin/env python3
"""Read-only targeted SQL snapshot through existing SSH master. Never restores."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

TABLES = {
 'category5_object': ['object_id','country_code','product_code','object_name','creation_date','parent_object_id'],
 'category5_attr': ['object_id','attribute_name','creation_date','sync_type_id','last_change_date','attribute_value'],
}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    parser.add_argument('--control-path',default='/tmp/gt-baseline-ssh-%u')
    args=parser.parse_args()
    os.umask(0o077)
    args.output.mkdir(mode=0o700,parents=False,exist_ok=False)
    # One native serializable transaction, one connection, no persistent writes.
    import uuid
    token='GT_SNAPSHOT_'+uuid.uuid4().hex
    statements=['\\set ON_ERROR_STOP on','BEGIN;', 'SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;']
    for table, cols in TABLES.items():
        prefix='INSERT INTO '+table+' ('+','.join(cols)+') VALUES ('
        values=" || ',' || ".join("COALESCE(quote_literal(%s::text),'NULL')"%c for c in cols)
        statements += ["SELECT '%s_%s_BEGIN';"%(token,table),
            "SELECT '%s' || %s || ');' FROM %s WHERE object_id IN (1,5,6) ORDER BY %s;"%(prefix,values,table,','.join(cols[:2])),
            "SELECT '%s_%s_END';"%(token,table),
            'SELECT count(*) FROM %s WHERE object_id IN (1,5,6);'%table]
    statements += ['ROLLBACK;']
    result=subprocess.run(['ssh','-S',args.control_path,'-o','BatchMode=yes',
        '-o','ConnectTimeout=8','operator@192.0.2.124',
        '/usr/local/pgsql/bin/psql -U postgres -d GameDB -qAt'],
        input='\n'.join(statements),text=True,capture_output=True)
    if result.returncode or result.stderr.strip():
        raise RuntimeError('Atomic read-only snapshot failed; values withheld')
    report={}
    for table in TABLES:
        begin=token+'_'+table+'_BEGIN\n';end=token+'_'+table+'_END\n'
        if result.stdout.count(begin)!=1 or result.stdout.count(end)!=1:
            raise RuntimeError('Invalid snapshot framing')
        section=result.stdout.split(begin,1)[1]
        sql,tail=section.split(end,1)
        rows=int(tail.splitlines()[0])
        if rows and not sql.startswith('INSERT INTO '+table+' ('):
            raise RuntimeError('Invalid snapshot SQL')
        raw=sql.encode();(args.output/(table+'.sql')).write_bytes(raw)
        report[table]={'rows':rows,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
    report['scope']='Read-only export in one SERIALIZABLE transaction; ROLLBACK; not a restore proof'
    (args.output/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
