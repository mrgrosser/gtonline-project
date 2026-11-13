#!/usr/bin/env python2
"""Bounded startup helper; public-context refresh then guarded GDB application."""
from __future__ import print_function
import os,time,subprocess,json,sys
anchor=int(sys.argv[1]);start=os.times()[4]
assert abs(time.time()-anchor)<5, 'Host/cabinet clock mismatch at arming'
while os.times()[4]-start<120:
    with open('/tmp/gt-public-refresh.log','w') as out:
        result=subprocess.call(['python','/tmp/refresh_public_context.py'],stdout=out,stderr=out)
    if result==0:
        predicted=anchor+(os.times()[4]-start)
        assert abs(time.time()-predicted)<5, 'System clock drifted during startup'
        p='/tmp/gt-trust-drill-config.json';c=json.load(open(p));c['verified_clock_epoch']=int(time.time())
        with open(p,'w') as f:json.dump(c,f)
        env=os.environ.copy();env['GT_TRUST_MODE']='apply'
        with open('/tmp/gt-startup-trust.log','w') as out:
            result=subprocess.call(['gdb','-q','-nx','-batch','-ex','source /tmp/gdb_public_trust_drill.py'],env=env,stdout=out,stderr=out)
        if result:raise RuntimeError('GDB failed; retain isolation')
        r=json.load(open('/tmp/gt-private-trust-applied.json'));assert r['applied'] and r['passed']
        os.chown('/tmp/gt-private-trust-applied.json',1004,1004)
        print('Private RAM trust applied and verified');break
    time.sleep(.25)
else:raise RuntimeError('No ready public context within120seconds; retain isolation')
