"""Read-only policy validation; no automatic rule removal after possible writes."""
import json,os
from pathlib import Path
INTERNAL='00000000-0000-4000-8000-000000000001'
EXTERNAL='00000000-0000-4000-8000-000000000002'
MAC='02:00:00:00:00:01'
def validate(policy,policy_id):
    expected_source={'zoneId':INTERNAL,'trafficFilter':{'type':'MAC_ADDRESS','macAddressFilter':{'macAddresses':[MAC]}}}
    if not (policy.get('id')==policy_id and policy.get('enabled') is True
        and policy.get('action')=={'type':'BLOCK'}
        and policy.get('source')==expected_source
        and policy.get('destination')=={'zoneId':EXTERNAL}
        and policy.get('ipProtocolScope')=={'ipVersion':'IPV4_AND_IPV6'}
        and not policy.get('schedule') and not policy.get('connectionStateFilter')
        and not policy.get('ipsecFilter')
        and isinstance(policy.get('index'),int) and policy['index']<30000):
        raise RuntimeError('Cabinet isolation policy does not match verified guard')
def authorize(fetch_policy,policy_id,journal,boot_id):
    validate(fetch_policy(),policy_id)
    # Exclusive durable marker precedes send: crash during send is treated as
    # possibly modified storage. Operator must verify recovery before unblock.
    data={'state':'positive_reply_may_have_been_sent','policy_id':policy_id,
          'boot_id':boot_id,'cabinet_mac':MAC,'automatic_unblock_allowed':False}
    fd=os.open(str(journal),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as f:
        json.dump(data,f);f.flush();os.fsync(f.fileno())
    fd=os.open(str(Path(journal).parent),os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)
