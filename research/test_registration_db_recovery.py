#!/usr/bin/env python3
"""Test saved SQL restoration in native PostgreSQL TEMP tables; always ROLLBACK.
Never DELETE/UPDATE/INSERT persistent cabinet tables. Only reads their structure.
"""
from pathlib import Path
import subprocess
import json
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parent
BACKUP=ROOT/'backups/registration-rows-20261112'

def inserts(table,target):
    raw=(BACKUP/(table+'.sql')).read_text()
    prefix='INSERT INTO '+table+' ('
    assert raw.startswith(prefix)
    # Exact generated SQL table token; values remain quoted by native quote_literal.
    return raw.replace(prefix,'INSERT INTO '+target+' (')

sql=['\\set ON_ERROR_STOP on','BEGIN;']
for source,suffix in [('category5_object','obj'),('category5_attr','attr')]:
    gold='gt_check_gold_'+suffix;work='gt_check_work_'+suffix
    sql.extend(['CREATE TEMP TABLE '+gold+' AS SELECT * FROM '+source+' WHERE 1=0;',
                inserts(source,gold),
                'CREATE TEMP TABLE '+work+' AS SELECT * FROM '+gold+';'])
# Mirror the inspected constraints entirely within temporary tables. Never attach
# triggers/FKs to persistent tables or consume the persistent ID sequence.
sql += ['CREATE TEMP TABLE gt_check_sync AS SELECT sync_type_id FROM itnet_sync_types;',
        'ALTER TABLE gt_check_sync ALTER COLUMN sync_type_id SET NOT NULL;',
        'ALTER TABLE gt_check_sync ADD PRIMARY KEY (sync_type_id);',
        'ALTER TABLE gt_check_work_obj ALTER COLUMN object_id SET NOT NULL;',
        'ALTER TABLE gt_check_work_obj ADD PRIMARY KEY (object_id);',
        'ALTER TABLE gt_check_work_obj ADD UNIQUE (country_code, product_code, object_name);',
        'ALTER TABLE gt_check_work_attr ALTER COLUMN object_id SET NOT NULL;',
        'ALTER TABLE gt_check_work_attr ALTER COLUMN attribute_name SET NOT NULL;',
        'ALTER TABLE gt_check_work_attr ADD PRIMARY KEY (object_id, attribute_name);',
        'ALTER TABLE gt_check_work_attr ADD FOREIGN KEY (object_id) REFERENCES gt_check_work_obj(object_id) ON DELETE CASCADE;',
        'ALTER TABLE gt_check_work_attr ADD FOREIGN KEY (sync_type_id) REFERENCES gt_check_sync(sync_type_id);']
for suffix, columns in [('obj',['country_code','product_code','object_name','creation_date']),
                        ('attr',['creation_date','sync_type_id'])]:
    for column in columns:
        sql.append('ALTER TABLE gt_check_work_'+suffix+' ALTER COLUMN '+column+' SET NOT NULL;')
sql += ["UPDATE gt_check_work_obj SET object_name='OFFLINE_RECOVERY_TEST_' || object_id;",
        "UPDATE gt_check_work_attr SET attribute_value='OFFLINE_RECOVERY_TEST';",
        'DELETE FROM gt_check_work_obj WHERE object_id=6;',
        "SELECT 'cascade_remaining',count(*) FROM gt_check_work_attr WHERE object_id=6;",
        'DELETE FROM gt_check_work_attr;', 'DELETE FROM gt_check_work_obj;',
        inserts('category5_object','gt_check_work_obj'),inserts('category5_attr','gt_check_work_attr')]
for suffix in ['obj','attr']:
    gold='gt_check_gold_'+suffix;work='gt_check_work_'+suffix
    sql.append("SELECT '%s_count',count(*) FROM %s;"%(suffix,work))
    sql.append("SELECT '%s_differences',count(*) FROM ((SELECT * FROM %s EXCEPT SELECT * FROM %s) UNION ALL (SELECT * FROM %s EXCEPT SELECT * FROM %s)) AS differences;"%(suffix,work,gold,gold,work))
sql += ['ROLLBACK;']
# No script written to disk: snapshot may contain private encrypted session data.
r=subprocess.run(['ssh','-S','/tmp/gt-baseline-ssh-%u','-o','BatchMode=yes','operator@192.0.2.124',
                  '/usr/local/pgsql/bin/psql -U postgres -d GameDB -At'],input='\n'.join(sql),text=True,capture_output=True)
if r.returncode or any(line.startswith(('ERROR:', 'FATAL:')) for line in r.stderr.splitlines()):
    # Do not print SQL/value-bearing diagnostics.
    raise RuntimeError('Temporary-table recovery test failed; no live table writes were issued')
expected={'obj_count|3','attr_count|15','obj_differences|0','attr_differences|0','cascade_remaining|0'}
found={line.strip() for line in r.stdout.splitlines() if '|' in line}
assert found==expected,found
print('\n'.join(sorted(found)))
print('Native PostgreSQL temporary-table roundtrip passed; transaction rolled back; live tables read only')

evidence={'observed_at':datetime.now(timezone.utc).isoformat(),'checks':sorted(found),
          'constraints':'TEMP primary keys, unique object name, NOT NULL, object cascade FK, sync type FK',
          'persistent_writes':False,'transaction':'ROLLBACK',
          'limits':['Not a live restore','No hardware rollback','Snapshot not cross-table atomic','No concurrency test']}
(ROOT/'evidence'/'registration-db-recovery.json').write_text(json.dumps(evidence,indent=2)+'\n')
