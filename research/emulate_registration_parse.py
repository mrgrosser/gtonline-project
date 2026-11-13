#!/usr/bin/env python3
"""Offline native plaintext-v3 field parser test, NOT full response acceptance.
Starts after dispatcher setup and stops before logging/state mutation.
Only C++ string push_back is modeled. No cabinet/device/network access.
"""
import copy,json,struct
from emulate_storage_write import new_machine,STACK,BUF,UC_X86_REG_ESP,UC_X86_REG_EAX,UC_X86_REG_EIP,UC_HOOK_CODE,UC_HOOK_INTR
from unicorn.x86_const import UC_X86_REG_EBP, UC_X86_REG_EDI
from registration_fixture import Fixture,encode_messages

FIELDS={0x68:'POSTAL_CODE',0x80:'CITY',0x98:'LOCATION_NAME',0xb0:'ADDRESS',
        0xc8:'PHONE_NUMBER',0xe0:'FAX_NUMBER',0x110:'STATE'}

def run(name,values,continuation=None):
    body=encode_messages([(14007,3,values)])[3:]
    assert len(body)<0x1000
    uc=new_machine(); sp=STACK+0x8000
    uc.mem_write(BUF,body)
    uc.mem_write(BUF+0x1000,struct.pack('<II',BUF,len(body)))
    uc.mem_write(sp+0x2f8,struct.pack('<I',BUF+0x1000))
    uc.mem_write(sp+0x2c,struct.pack('<H',3))
    uc.reg_write(UC_X86_REG_ESP,sp)
    uc.reg_write(UC_X86_REG_EBP,14007)
    uc.reg_write(UC_X86_REG_EDI,len(body))
    strings={key:bytearray() for key in FIELDS}; stopped=False
    def word(a): return struct.unpack('<I',bytes(uc.mem_read(a,4)))[0]
    def hook(uc,addr,size,data):
        nonlocal stopped
        if addr==0x8960494:
            stopped=True; uc.emu_stop()
        elif addr==0x81d51f0:
            callsp=uc.reg_read(UC_X86_REG_ESP)
            obj=word(callsp+4); char=word(callsp+8)&255
            assert obj-sp in strings
            strings[obj-sp].append(char)
            uc.reg_write(UC_X86_REG_ESP,callsp+4)
            uc.reg_write(UC_X86_REG_EIP,word(callsp))
        elif not (0x8960115<=addr<0x8960494 or 0x89607a6<=addr<=0x89607ab):
            raise RuntimeError('Unexpected parser branch '+hex(addr))
    def interrupt(*args): raise RuntimeError('Guest interrupt prohibited')
    code_hook=uc.hook_add(UC_HOOK_CODE,hook); uc.hook_add(UC_HOOK_INTR,interrupt)
    uc.emu_start(0x8960115,0,count=100000)
    assert stopped
    parsed={FIELDS[k]:v.decode('latin1') for k,v in strings.items()}
    parsed.update(CABINET_OPERATOR_ID=word(sp+0x40),OPERATOR_ID=word(sp+0x38),
      GMT_OFFSET=struct.unpack('<h',bytes(uc.mem_read(sp+0xfc,2)))[0],
      DAYLIGHT_SAVINGS_FLAG=uc.mem_read(sp+0x100,1)[0],
      CABINET_STANDING=uc.mem_read(sp+0xfe,1)[0],
      COUNTRY_CODE=word(sp+0x104),CUSTOMER_CODE=word(sp+0x108),SECURITY_CODE=word(sp+0x10c))
    for k,v in parsed.items(): assert v==values[k],(k,v,values[k])
    if continuation is not None:
        uc.hook_del(code_hook)
        return continuation(uc,sp)
    return {'case':name,'native_fields_matched':len(parsed),'payload_bytes':len(body),
            'full_handler_executed':False,'persistent_writes':False}

def main():
    rows=[]
    for mode in ('baseline','local-example'):
        values=next(v for m,version,v in Fixture(mode).messages if m==14007)
        rows.append(run(mode,values))
    varied=copy.deepcopy(values)
    varied.update(CABINET_OPERATOR_ID=0x1020304,OPERATOR_ID=0x5060708,
      POSTAL_CODE='55401',CITY='TEST CITY',LOCATION_NAME='OFFLINE FIXTURE',
      ADDRESS='123 TEST',PHONE_NUMBER='5550100',FAX_NUMBER='5550101',STATE='MN',
      GMT_OFFSET=-6,DAYLIGHT_SAVINGS_FLAG=1,CABINET_STANDING=2,
      COUNTRY_CODE=3,CUSTOMER_CODE=4,SECURITY_CODE=5)
    rows.append(run('varied_synthetic_fields',varied))
    print(json.dumps({'scope':'native parser section; C++ strings modeled; stops before state changes',
                     'signature_validation_tested':False,'cases':rows},indent=2))
if __name__=='__main__': main()
