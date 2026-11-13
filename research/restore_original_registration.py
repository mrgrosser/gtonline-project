#!/usr/bin/env python2
"""Explicit original-byte restore at maintenance gate; never launches game.
Default compare-only. Requires exact boot and SHA256-pinned post-test preimages.
DB/process recovery is separate; do not clear isolation until independently done.
"""
from __future__ import print_function
import argparse,hashlib,json,os,subprocess
from registration_storage_drill import Cabinet,validate
from registration_recovery_model import restore_original

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--boot-id',required=True);p.add_argument('--original',required=True)
    p.add_argument('--current-2',required=True);p.add_argument('--current-3',required=True)
    p.add_argument('--sha256-2',required=True);p.add_argument('--sha256-3',required=True)
    p.add_argument('--apply-original',action='store_true');a=p.parse_args()
    if os.geteuid()!=0:raise ValueError('Root maintenance session required')
    with open('/proc/sys/kernel/random/boot_id') as f:boot=f.read().strip()
    if boot!=a.boot_id:raise ValueError('Boot changed')
    if subprocess.call(['pidof','go'],stdout=subprocess.PIPE)==0:
        raise ValueError('Game still running; refusing device access')
    if not os.path.isfile('/game/dynamic/gt-compat/positive-test.pending'):
        raise ValueError('No pending isolated experiment')
    with open(a.original,'rb') as f:original=f.read()
    validate(original);current={}
    for block in (2,3):
        with open(getattr(a,'current_'+str(block)),'rb') as f:raw=f.read()
        if len(raw)!=512 or hashlib.sha256(raw).hexdigest()!=getattr(a,'sha256_'+str(block)):
            raise ValueError('Preimage integrity failure')
        current[block]=raw
    device=Cabinet(a.apply_original)
    try:result=restore_original(device,original,current,a.apply_original)
    finally:device.close()
    print(json.dumps(result))
    print('Isolation retained. Database and process recovery still require verification.')
if __name__=='__main__':main()
