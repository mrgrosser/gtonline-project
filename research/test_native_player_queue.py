"""Original base request-context lookup with a synthetic database boundary.
No SQL is executed. Missing-map diagnostic path stops before logging/return.
"""
import struct
import unittest
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP
from emulate_player_payload import FieldMachine


class QueueMachine(FieldMachine):
    def __init__(self, map_present=True, queue_present=True, backend=True):
        super().__init__()
        self.map_present=map_present;self.queue_present=queue_present
        self.queries=[];self.bindings={};self.outputs={};self.stage=0
        self.missing_map=False
        self.row=(183,3,0x123456789abcdef0)
        self.destination=(b'synthetic.player',7,-1)
        self.owner=self.alloc(128);self.result=self.alloc(8);self.context=self.alloc(64)
        self.set_string(self.context+8,b'unchanged')
        self.factory=self.alloc(4);factory_vtable=self.alloc(4)
        self.statement=self.alloc(48);statement_vtable=self.alloc(24)
        self.put(self.factory,factory_vtable);self.put(self.statement,statement_vtable)
        self.callbacks={}
        for name in ('prepare','execute','fetch','close'):
            address=self.alloc(16);self.callbacks[address]=name
            self.uc.hook_add(UC_HOOK_CODE,self.hook,begin=address,end=address)
        byname={name:address for address,name in self.callbacks.items()}
        self.put(factory_vtable,byname['prepare'])
        for offset,address in ((4,0x088f94d6),(8,0x088f94e4),(12,byname['execute']),(16,byname['fetch']),(20,byname['close'])):
            self.put(statement_vtable+offset,address)
        self.put(self.owner+0x54,self.factory if backend else 0)
        for address in (0x08a5a2c0,0x08a5a6a2,0x08a5a67e,0x08a5a8d6,0x08a5a300,0x08967820):
            self.uc.hook_add(UC_HOOK_CODE,self.hook,begin=address,end=address)

    def hook(self,u,address,size,data):
        sp=u.reg_read(UC_X86_REG_ESP);arg=lambda i:self.word(sp+4+4*i)
        name=self.callbacks.get(address) if hasattr(self,'callbacks') else None
        if name=='prepare':
            query=arg(1)
            if query not in (0x08bf8ef8,0x08bf901c):raise RuntimeError('Unexpected query')
            self.stage+=1;self.queries.append(query);self.ret(self.statement)
        elif name=='execute':self.ret(0)
        elif name=='fetch':
            present=self.map_present if self.stage==1 else self.queue_present
            self.put(arg(2),int(present))
            if present:
                p=self.outputs[self.word(self.statement+0x28)]
                if self.stage==1:
                    mid,version,rid=self.row
                    u.mem_write(p+8,struct.pack('<H',mid));u.mem_write(p+16,bytes([version]));u.mem_write(p+24,struct.pack('<Q',rid))
                else:
                    obj,category,completion=self.destination
                    u.mem_write(p+8,obj+b'\0');u.mem_write(p+0x10c,struct.pack('<H',category));u.mem_write(p+0x114,struct.pack('<h',completion))
            self.ret(0)
        elif name=='close':self.ret()
        elif address==0x08a5a2c0:self.bindings[arg(0)]=[];self.ret()
        elif address==0x08a5a6a2:
            self.bindings.setdefault(arg(0),[]).append(bytes(u.mem_read(arg(1)+4,8)));self.ret()
        elif address==0x08a5a67e:self.outputs[arg(0)]=arg(1);self.ret()
        elif address in (0x08a5a8d6,0x08a5a300):self.ret()
        elif address==0x08967820:self.missing_map=True;self.ended=True;u.emu_stop()
        elif address==0x081d4a40:
            p,pos,n,source,length=[arg(i) for i in range(5)]
            old=self.string(p);self.set_string(p,old[:pos]+bytes(u.mem_read(source,length))+old[pos+n:]);self.ret(p)
        else:super().hook(u,address,size,data)

    def run(self,cid=0x8123,offset=5):
        self.invoke(0x08967488,[self.result,self.owner,cid,offset,self.context],count=100000)
        return struct.unpack('<H2xI',self.uc.mem_read(self.result,8))


class NativePlayerQueueTests(unittest.TestCase):
    def test_no_backend_returns_native_error_without_query(self):
        m=QueueMachine(backend=False)
        self.assertEqual(m.run(),(0x433,0));self.assertEqual(m.queries,[])

    def test_missing_map_takes_diagnostic_branch_before_queue_query(self):
        m=QueueMachine(map_present=False);m.run()
        self.assertTrue(m.missing_map);self.assertEqual(m.queries,[0x08bf8ef8])
        self.assertEqual(m.string(m.context+8),b'unchanged')

    def test_missing_queue_returns_native_error(self):
        m=QueueMachine(queue_present=False)
        self.assertEqual(m.run(),(0x461,0));self.assertEqual(len(m.queries),2)
        self.assertEqual(m.string(m.context+8),b'unchanged')

    def test_matching_rows_populate_original_context(self):
        m=QueueMachine();self.assertEqual(m.run(),(0,0))
        self.assertEqual(bytes(m.uc.mem_read(m.context,3)),b'\xb7\x00\x03')
        self.assertEqual(m.word(m.context+4),7)
        self.assertEqual(m.string(m.context+8),b'synthetic.player')
        self.assertEqual(struct.unpack('<Q',m.uc.mem_read(m.context+32,8))[0],m.row[2])
        self.assertEqual(m.word(m.context+40),0xffffffff)

    def test_native_binding_widths_and_request_id(self):
        m=QueueMachine();m.run(0x8123,0x105)
        values=[v for group in m.bindings.values() for v in group]
        self.assertEqual(int.from_bytes(values[0][:2],'little'),0x8123)
        self.assertEqual(int.from_bytes(values[1][:2],'little'),5)
        self.assertEqual(int.from_bytes(values[2],'little'),m.row[2])

    def test_empty_object_and_unsigned_category_signed_completion(self):
        m=QueueMachine();m.destination=(b'',65535,-32768)
        self.assertEqual(m.run(),(0,0));self.assertEqual(m.string(m.context+8),b'')
        self.assertEqual(m.word(m.context+4),65535)
        self.assertEqual(m.word(m.context+40),0xffff8000)


if __name__=='__main__':unittest.main()
