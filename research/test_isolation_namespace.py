#!/usr/bin/env python2
"""Kernel routing integration in NEW network namespace only; no cabinet routes changed."""
from __future__ import print_function
import ctypes,json,subprocess
from prepare_management_route import plan
lib=ctypes.CDLL(None,use_errno=True)
if lib.unshare(0x40000000)!=0:raise OSError(ctypes.get_errno(),'new network namespace unavailable; no route commands issued')
IP='/sbin/ip'
def call(*args):subprocess.check_call([IP]+list(args))
call('link','set','lo','up');call('addr','add','192.0.2.124/24','dev','lo')
call('route','add','default','via','192.0.2.1','dev','lo','metric','202')
before=subprocess.check_output([IP,'route','get','198.51.100.8']).decode().splitlines()[0]
subprocess.check_call(plan('198.51.100.8',before))
call('route','add','blackhole','default','metric','1')
call('route','add','local','203.0.113.49/32','dev','lo','table','local','metric','42761')
after=subprocess.check_output([IP,'route','get','198.51.100.8']).decode().splitlines()[0]
assert plan('198.51.100.8',after)==plan('198.51.100.8',before)
p=subprocess.Popen([IP,'route','get','1.1.1.1'],stdout=subprocess.PIPE,stderr=subprocess.PIPE);p.communicate();assert p.returncode!=0
vendor=subprocess.check_output([IP,'route','get','203.0.113.49']).decode();assert vendor.startswith('local ')
call('-6','route','add','blackhole','default','metric','1')
p=subprocess.Popen([IP,'-6','route','get','2606:4700:4700::1111'],stdout=subprocess.PIPE,stderr=subprocess.PIPE);p.communicate();assert p.returncode!=0
print(json.dumps({'management_route_preserved':True,'vendor_local':True,'ipv4_external_blocked':True,'ipv6_external_blocked':True,'scope':'new isolated kernel network namespace only'}))
