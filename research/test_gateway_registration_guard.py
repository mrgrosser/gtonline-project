import copy,tempfile,json
from pathlib import Path
from gateway_registration_guard import *
p={'id':'test','enabled':True,'action':{'type':'BLOCK'},'source':{'zoneId':INTERNAL,'trafficFilter':{'type':'MAC_ADDRESS','macAddressFilter':{'macAddresses':[MAC]}}},'destination':{'zoneId':EXTERNAL},'ipProtocolScope':{'ipVersion':'IPV4_AND_IPV6'},'index':10000}
with tempfile.TemporaryDirectory() as tmp:
    journal=Path(tmp)/'pending.json'
    cases=[('enabled',False),('action',{'type':'ALLOW'}),('destination',{'zoneId':INTERNAL}),('schedule',{'mode':'EVERY_DAY'}),('connectionStateFilter',['NEW']),('index',40000),('ipProtocolScope',{'ipVersion':'IPV4'})]
    for k,v in cases:
        bad=copy.deepcopy(p);bad[k]=v
        try:authorize(lambda:bad,'test',journal,'boot')
        except RuntimeError:pass
        else:raise AssertionError(k)
        assert not journal.exists()
    authorize(lambda:p,'test',journal,'boot')
    assert json.loads(journal.read_text())['automatic_unblock_allowed'] is False
    try:authorize(lambda:p,'test',journal,'boot')
    except FileExistsError:pass
    else:raise AssertionError('duplicate journal accepted')
print('9 guard cases passed (7 reject; durable authorization; duplicate refusal)')
