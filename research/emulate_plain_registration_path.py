#!/usr/bin/env python3
"""Native plaintext parser + branch path up to save entry; no persistent operations."""
import copy,json,struct
from emulate_registration_parse import run as parse
from emulate_storage_write import BUF
from registration_fixture import Fixture
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_EIP,UC_X86_REG_EAX

def run_case(name,ids,old=(0,0),signature=b'\0'*40,save_result=None):
    values=copy.deepcopy(next(v for m,ver,v in Fixture('local-example').messages if m==14007))
    values.update(CABINET_OPERATOR_ID=ids[0],OPERATOR_ID=ids[1],ENCRYPTION_SIGNATURE=signature)
    def continuation(uc,sp):
        state=list(old);writes=[];stop=None;manager=BUF+0x1400;session=BUF+0x1500
        uc.mem_write(sp+0x2f0,struct.pack('<I',BUF+0x1800))
        def word(a):return struct.unpack('<I',uc.mem_read(a,4))[0]
        def ret(v=0,pop=4):
            s=uc.reg_read(UC_X86_REG_ESP);uc.reg_write(UC_X86_REG_EAX,v)
            uc.reg_write(UC_X86_REG_EIP,word(s));uc.reg_write(UC_X86_REG_ESP,s+pop)
        def hook(u,a,size,data):
            nonlocal stop
            s=u.reg_read(UC_X86_REG_ESP)
            if a==0x08a0b034:
                if save_result is None:
                    stop='save_entry';u.emu_stop()
                else:
                    out=word(s+4)
                    u.mem_write(out,struct.pack('<H2xI',*save_result))
                    ret(out,pop=8)
            elif a==0x08960b75:
                stop='post_save_success';u.emu_stop()
            elif a==0x08960e30:
                stop='error_cleanup';u.emu_stop()
            elif a==0x08961b1f:
                stop='unchanged_ids_branch';u.emu_stop()
            elif a==0x08a0b728:ret(manager)
            elif a==0x08a08b28:ret(state[0])
            elif a==0x08a08a9e:ret(state[1])
            elif a in (0x08a08b6c,0x08a08ae2):
                i=0 if a==0x08a08b6c else 1
                assert word(s+4)==manager
                state[i]=word(s+8);writes.append(i);ret()
            elif a==0x08931c9e:ret(session)
            elif a==0x08a52a66:ret(BUF+0x1700)
            elif a==0x08a52a98:ret()
            elif a in (0x081d3b20,0x081d39d0):ret()
            elif a in (0x081d46a0,0x081d3d20):ret(word(s+4))
            elif a==0x081d3a20:
                out=word(s+4);u.mem_write(out,struct.pack('<II',out+8,0));u.mem_write(out+8,b'\0');ret(out,pop=8)
            elif not (0x08960494<=a<0x089607b1 or 0x089611c2<=a<=0x0896133d or 0x08931fbc<=a<=0x08931fca):
                raise RuntimeError('Unexpected branch '+hex(a))
        uc.hook_add(UC_HOOK_CODE,hook)
        uc.emu_start(0x08960494,0,count=100000)
        assert stop
        expected=list(ids) if all(ids) else [0,0]
        if ids==old and all(ids):assert stop=='unchanged_ids_branch' and not writes
        else:
            target='save_entry' if save_result is None else 'post_save_success' if save_result[0]==0 else 'error_cleanup'
            assert stop==target and state==expected and writes==[0,1]
        reported_error=None
        if stop=='error_cleanup':
            reported_error=struct.unpack('<H2xI',uc.mem_read(BUF+0x1800,8))
            assert reported_error==save_result
        return dict(case=name,stop=stop,modeled_ids=state,registration_change_flag=bool(uc.mem_read(session+0x19,1)[0]),
                    save_executed=False,modeled_save_result=save_result,reported_error=reported_error,
                    signature_pattern='zero' if not any(signature) else 'synthetic_nonzero')
    return parse(name,values,continuation)

if __name__=='__main__':
    cases=[run_case('new_nonzero_ids',(1,1)),run_case('new_ids_nonzero_signature',(1,1),signature=b'Z'*40),
           run_case('zero_ids',(0,0)),run_case('operator_zero',(1,0)),run_case('cabinet_operator_zero',(0,1)),
           run_case('unchanged_nonzero_ids',(1,1),(1,1)),
           run_case('save_success',(1,1),save_result=(0,0)),
           run_case('save_io_error',(1,1),save_result=(0x100,5)),
           run_case('save_generic_error',(1,1),save_result=(0x482,0))]
    print(json.dumps({'scope':'native plaintext parser and branch-to-save; logging and ID accessors modeled; dispatcher and storage excluded','cases':cases},indent=2))
