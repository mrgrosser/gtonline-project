"""Native Nighthawk completion reader with synthetic DB boundaries.
No SQL or game code is run outside Unicorn. Native reader branches execute;
Six methods model channel classification; one executes the original classifier.
"""
import struct
import unittest
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP
import test_native_player_queue as queue_fixture


class CompletionReaderMachine(queue_fixture.QueueMachine):
    def __init__(self, status=1, channel=7, mapped_channel=False,
                 present=True, backend=True, failure=None, native_channel=False):
        super().__init__(backend=backend, failure=failure)
        self.status=status; self.channel=channel
        self.mapped_channel=mapped_channel; self.present=present
        self.channel_calls=[]
        self.put(self.owner+4,self.factory if backend else 0)
        self.request_id=self.alloc(8)
        self.uc.mem_write(self.request_id,struct.pack('<Q',0x123456789abcdef0))
        for address in ((0x088e8872,) if native_channel else (0x088e8872,0x088e9e2a)):
            self.uc.hook_add(UC_HOOK_CODE,self.hook,begin=address,end=address)

    def hook(self,u,address,size,data):
        sp=u.reg_read(UC_X86_REG_ESP)
        arg=lambda i:self.word(sp+4+4*i)
        name=self.callbacks.get(address) if hasattr(self,'callbacks') else None
        if name=='prepare':
            if arg(1)!=0x08bf35e0:raise RuntimeError('Unexpected completion query')
            self.stage+=1; self.queries.append(arg(1)); self.ret(self.statement)
        elif name=='fetch':
            self.operations.append((self.stage,name))
            if self.failure==(self.stage,name):self.ret(9);return
            self.put(arg(2),int(self.present))
            if self.present:
                p=self.outputs[self.word(self.statement+0x28)]
                u.mem_write(p+8,struct.pack('<h',self.status))
                u.mem_write(p+16,struct.pack('<H',self.channel))
            self.ret(0)
        elif address==0x088e8872:self.ret(self.owner)
        elif address==0x088e9e2a:
            self.channel_calls.append(arg(1));self.ret(int(self.mapped_channel))
        else:super().hook(u,address,size,data)

    def read(self):
        return self.invoke(0x08900c44,[self.owner,self.request_id],count=100000)


class NativeITNetCompletionTests(unittest.TestCase):
    def test_no_database_returns_zero_without_query(self):
        m=CompletionReaderMachine(backend=False)
        self.assertEqual(m.read(),0);self.assertEqual(m.queries,[])

    def test_missing_row_returns_three(self):
        m=CompletionReaderMachine(present=False)
        self.assertEqual(m.read(),3);self.assertEqual(m.channel_calls,[])

    def test_unmapped_channel_preserves_status_except_minus_one(self):
        for status in (-32768,-1,0,1,2,3,32767):
            with self.subTest(status=status):
                m=CompletionReaderMachine(status=status)
                self.assertEqual(m.read(),0 if status==-1 else status)
                self.assertEqual(m.channel_calls,[] if status==-1 else [7])

    def test_modeled_mapped_channel_reduces_status_to_success_boolean(self):
        for status in (-32768,-1,0,1,2,3,32767):
            with self.subTest(status=status):
                m=CompletionReaderMachine(status=status,mapped_channel=True,channel=65535)
                self.assertEqual(m.read(),int(status==1))
                self.assertEqual(m.channel_calls,[] if status==-1 else [65535])

    def test_execute_and_fetch_failures_return_zero_not_missing_row_three(self):
        for operation in ('execute','fetch'):
            with self.subTest(operation=operation):
                m=CompletionReaderMachine(failure=(1,operation))
                self.assertEqual(m.read(),0)
                self.assertEqual(m.channel_calls,[])
                self.assertEqual(m.operations[-1],(1,'close'))
                if operation=='execute':self.assertNotIn((1,'fetch'),m.operations)

    def test_original_channel_classifier_and_reader(self):
        # Execute both original routines, not the modeled classifier hook.
        for channel in (0,1,2,3,4,5,6,7,255,256,32767,32768,65535):
            for status in (-1,0,1,3):
                with self.subTest(channel=channel,status=status):
                    m=CompletionReaderMachine(status=status,channel=channel,
                                              native_channel=True)
                    expected=0 if status==-1 else (
                        int(status==1) if channel in (1,2,3,6) else status)
                    self.assertEqual(m.read(),expected)
                    self.assertEqual(m.channel_calls,[])

    def test_request_id_binding_preserves_full_64_bits(self):
        m=CompletionReaderMachine();self.assertEqual(m.read(),1)
        values=[value for group in m.bindings.values() for value in group]
        self.assertEqual(values,[struct.pack('<Q',0x123456789abcdef0)])
        self.assertEqual(m.queries,[0x08bf35e0])


if __name__=='__main__':unittest.main()
