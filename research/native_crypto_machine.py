"""Offline x86 runner: native crypto, modeled RAM allocation and libc only."""
import struct
from emulate_storage_write import new_machine,STACK,BUF,STOP
from unicorn import UC_HOOK_CODE,UC_HOOK_INTR
from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_EAX,UC_X86_REG_EIP

class Machine:
    def __init__(self, fixed_time=None):
        self.fixed_time=fixed_time
        self.uc=new_machine();self.heap=0x33000000;self.uc.mem_map(self.heap,0x1000000)
        self.allocations={};self.free_bins={};self.ended=False
        addresses=(STOP,0x08a817b0,0x08a71f70,0x08a81480,0x08a81690,0x08a720a0,0x08a81530,0x08a81440,0x08b6aaa6)
        for address in addresses:self.uc.hook_add(UC_HOOK_CODE,self.hook,begin=address,end=address)
        self.uc.hook_add(UC_HOOK_CODE,self.hook,begin=0x081d3000,end=0x081d5fff)
        self.uc.hook_add(UC_HOOK_INTR,lambda *args: (_ for _ in ()).throw(RuntimeError('Guest syscall forbidden')))
    def word(self,a):return struct.unpack('<I',self.uc.mem_read(a,4))[0]
    def put(self,a,v):self.uc.mem_write(a,struct.pack('<I',v))
    def alloc(self,n):
        assert 0<n<=0x100000
        size=(n+15)&~15
        if self.free_bins.get(size):p=self.free_bins[size].pop()
        else:
            p=self.heap;self.heap+=size;assert self.heap<0x34000000
        self.uc.mem_write(p,bytes(size))
        self.allocations[p]=size;return p
    def free(self,p):
        if p in self.allocations:
            size=self.allocations.pop(p);self.free_bins.setdefault(size,[]).append(p)
    def ret(self,v=0):
        s=self.uc.reg_read(UC_X86_REG_ESP);self.uc.reg_write(UC_X86_REG_EAX,v&0xffffffff)
        self.uc.reg_write(UC_X86_REG_EIP,self.word(s));self.uc.reg_write(UC_X86_REG_ESP,s+4)
    def hook(self,u,a,size,data):
        s=u.reg_read(UC_X86_REG_ESP)
        if a==STOP:self.ended=True;u.emu_stop()
        elif a in (0x08a817b0,0x08a71f70,0x08a81480):
            self.ret(self.alloc(self.word(s+8)*(4 if a==0x08a71f70 else 1)))
        elif a in (0x081d31d0,0x081d3fc0,0x08b6aaa6):self.ret(self.alloc(self.word(s+4)))
        elif a in (0x08a81690,0x08a720a0):self.free(self.word(s+8));self.ret()
        elif a in (0x081d3980,0x081d3e70,0x081d3c80):self.free(self.word(s+4));self.ret()
        elif a in (0x08a81530,0x08a81440):self.ret()
        elif a in (0x081d3540,0x081d3560):
            d,p,n=[self.word(s+i) for i in (4,8,12)]
            u.mem_write(d,bytes(u.mem_read(p,n)));self.ret(d)
        elif a==0x081d4330:
            d,v,n=[self.word(s+i) for i in (4,8,12)]
            u.mem_write(d,bytes([v&255])*n);self.ret(d)
        elif a==0x081d42a0:
            p,q,n=[self.word(s+i) for i in (4,8,12)]
            left=bytes(u.mem_read(p,n));right=bytes(u.mem_read(q,n))
            self.ret((left>right)-(left<right))
        elif a==0x081d3120 and self.fixed_time is not None:self.ret(self.fixed_time)
        else:raise RuntimeError('Unexpected PLT %x'%a)
    def invoke(self,address,args,count=100000000):
        self.ended=False;s=STACK+0x8000
        self.uc.mem_write(s,struct.pack('<'+'I'*(len(args)+1),STOP,*args))
        self.uc.reg_write(UC_X86_REG_ESP,s)
        self.uc.emu_start(address,STOP+1,count=count)
        assert self.ended,'Native instruction budget exhausted'
        v=self.uc.reg_read(UC_X86_REG_EAX);return v if v<2**31 else v-2**32

def der_integers(der):
    def tlv(pos):
        tag=der[pos];n=der[pos+1];pos+=2
        if n&128:
            k=n&127;n=int.from_bytes(der[pos:pos+k],'big');pos+=k
        return tag,pos,pos+n
    tag,pos,end=tlv(0);assert tag==0x30 and end==len(der)
    out=[]
    while pos<end:
        tag,start,pos=tlv(pos);assert tag==2;out.append(int.from_bytes(der[start:pos],'big'))
    return out
