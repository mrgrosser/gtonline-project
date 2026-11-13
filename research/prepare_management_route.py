#!/usr/bin/env python2
"""Pin ONLY the real SSH peer's current return route. Never changes defaults.
Run plan as SSH user with SSH_CONNECTION; root apply receives the inspected peer.
No replaces/deletes; refuses preexisting matching host route to avoid ownership ambiguity.
"""
from __future__ import print_function
import argparse,json,os,re,socket,subprocess
IP='/sbin/ip';METRIC='42763'
def ipv4(s):
    if not re.match(r'^\d+\.\d+\.\d+\.\d+$',s):raise ValueError('IPv4 peer required')
    socket.inet_aton(s)
    if any(int(x)>255 for x in s.split('.')):raise ValueError('IPv4 range')
    return s

def plan(peer,line):
    peer=ipv4(peer);words=line.split()
    if words[0]!=peer or 'dev' not in words or any(x in words for x in ('blackhole','unreachable','prohibit','local')):
        raise ValueError('Expected ordinary routed SSH peer')
    dev=words[words.index('dev')+1]
    if not re.match(r'^[A-Za-z0-9_.:-]+$',dev):raise ValueError('interface')
    cmd=[IP,'route','add',peer+'/32']
    if 'via' in words:cmd+=['via',ipv4(words[words.index('via')+1])]
    cmd+=['dev',dev,'metric',METRIC]
    return cmd

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--peer');p.add_argument('--apply',action='store_true');a=p.parse_args()
    connection=os.environ.get('SSH_CONNECTION','').split()
    peer=a.peer or (connection[0] if len(connection)==4 else '')
    if connection and peer!=connection[0]:raise ValueError('Peer does not match SSH connection')
    ipv4(peer)
    line=subprocess.check_output([IP,'route','get',peer]).decode().splitlines()[0]
    cmd=plan(peer,line)
    if a.apply:
        if os.geteuid()!=0:raise ValueError('root required')
        routes=subprocess.check_output([IP,'route','show','table','main']).decode().splitlines()
        if any(x.split()[0] in (peer,peer+'/32') for x in routes if x.split()):raise ValueError('Existing host route; inspect ownership first')
        subprocess.check_call(cmd)
        after=subprocess.check_output([IP,'route','get',peer]).decode().splitlines()[0]
        if plan(peer,after)!=cmd:raise ValueError('Post-add route mismatch; stop before isolation')
    print(json.dumps({'peer':peer,'command':cmd,'applied':a.apply,'defaults_changed':False}))
if __name__=='__main__':main()
