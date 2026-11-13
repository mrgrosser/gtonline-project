"""Offline native field loop. DB/dispatch/UI excluded; strings/libc modeled.
Harness-enforced payload bounds are NOT claims of native length validation.
"""
import struct
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EAX, UC_X86_REG_EDX, UC_X86_REG_ECX
from native_crypto_machine import Machine

class PayloadReadPastEnd(ValueError): pass

class FieldMachine(Machine):
    def __init__(self):
        super().__init__();self.parsed=None
        for a in (0x08a24326,0x08a3533e,0x08961d97):
            self.uc.hook_add(UC_HOOK_CODE,self.hook,begin=a,end=a)
    def cstring(self,p):
        result=bytearray()
        for i in range(65536):
            b=self.uc.mem_read(p+i,1)[0]
            if not b:return bytes(result)
            result.append(b)
        raise ValueError('unterminated fixture string')
    def string(self,p):
        n=self.word(p+4)
        if n>65536:raise ValueError('invalid fixture string length')
        return bytes(self.uc.mem_read(self.word(p),n)) if n else b''
    def set_string(self,p,value):
        dst=p+8 if len(value)<=15 else self.alloc(len(value)+1)
        self.put(p,dst);self.put(p+4,len(value))
        if len(value)>15:self.put(p+8,len(value))
        self.uc.mem_write(dst,value+b'\0')
    def hook(self,u,a,size,data):
        sp=u.reg_read(UC_X86_REG_ESP);arg=lambda i:self.word(sp+4+i*4)
        if a==0x08a24326:self.ret() # Outer container unused before stop.
        elif a==0x08961d97:
            start,end=self.word(sp+0x5c),self.word(sp+0x60)
            if not 0<=end-start<=24*256 or (end-start)%24:raise ValueError('invalid output vector')
            self.parsed=[self.string(p) for p in range(start,end,24)]
            self.ended=True;u.emu_stop()
        elif a==0x08a3533e:
            fmt=self.cstring(arg(2));number=arg(3)
            if fmt in (b'%d',b'%ld'):
                if number>=2**31:number-=2**32
            elif fmt not in (b'%u',b'%lu'):raise ValueError('unmodeled numeric format '+repr(fmt))
            out=str(number).encode()
            if len(out)+1>arg(1):raise ValueError('format buffer too small')
            u.mem_write(arg(0),out+b'\0');self.ret(len(out))
        elif a==0x081d3be0:self.ret(len(self.cstring(arg(0))))
        elif a==0x081d3c10:
            off=self.cstring(arg(0)).find(self.cstring(arg(1)));self.ret(0 if off<0 else arg(0)+off)
        elif a==0x081d5200:
            p,n,c=arg(0),arg(1),arg(2)&255
            if n>65536:raise ValueError('oversized resize')
            old=self.string(p);self.set_string(p,old[:n]+bytes([c])*max(0,n-len(old)));self.ret()
        elif a==0x081d43d0:self.ret(self.alloc(self.word(arg(1))+1))
        elif a==0x081d5090:self.set_string(arg(0),self.string(arg(1)));self.ret(arg(0))
        elif a==0x081d3170:
            p,pos,removed,source,n=arg(0),arg(1),arg(2),arg(3),arg(4)
            old=self.string(p)
            if pos>len(old) or removed>len(old)-pos or n>65536:raise ValueError('invalid modeled mutation')
            insert=bytes(u.mem_read(source,n)) if source and n else bytes(n)
            value=old[:pos]+insert+old[pos+removed:]
            capacity=max(len(value),len(old)*2,16)
            dst=self.alloc(capacity+1);u.mem_write(dst,value+b'\0')
            self.put(p,dst);self.put(p+8,capacity);self.ret()
        else:super().hook(u,a,size,data)
    def vector(self,values):
        p=self.alloc(12);raw=self.alloc(max(1,len(values)*2))
        if values:self.uc.mem_write(raw,struct.pack('<'+'H'*len(values),*values))
        for off,val in ((0,raw),(4,raw+len(values)*2),(8,raw+len(values)*2)):self.put(p+off,val)
        return p
    def parse(self,schema,body):
        if not schema or len(schema)>128 or len(body)>65536:raise ValueError('fixture exceeds bounds')
        names=self.alloc(12);raw=self.alloc(len(schema)*24)
        for i,(name,kind,length) in enumerate(schema):self.set_string(raw+i*24,name.encode('ascii'))
        for off,val in ((0,raw),(4,raw+len(schema)*24),(8,raw+len(schema)*24)):self.put(names+off,val)
        types=self.vector([t for _,t,_ in schema]);lengths=self.vector([n for _,_,n in schema])
        payload=self.alloc(24);base=0x35000000;self.uc.mem_map(base,0x12000);start=base+0x1000
        self.uc.mem_write(start,body+b'\0');self.put(payload,start);self.put(payload+4,len(body));self.put(payload+8,len(body))
        def bound(u,access,address,size,value,extra):
            if base<=address<base+0x12000 and not(start<=address and address+size<=start+len(body)):
                raise PayloadReadPastEnd('native field read exceeds supplied payload')
        self.uc.hook_add(UC_HOOK_MEM_READ,bound)
        cursor=self.alloc(4);result=self.alloc(8)
        self.uc.reg_write(UC_X86_REG_EAX,result);self.uc.reg_write(UC_X86_REG_EDX,0);self.uc.reg_write(UC_X86_REG_ECX,0)
        self.invoke(0x08961bf0,[0,payload,cursor,0,payload,2,names,types,lengths],count=1000000)
        if self.parsed is None:raise RuntimeError('field loop stop not reached')
        return self.parsed,self.word(cursor)

if __name__=='__main__':print(FieldMachine().parse([('VALUE',2,0)],b'\x01'))
