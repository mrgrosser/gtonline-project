"""Original common registry initializer; map insertion and strings modeled."""
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EAX, UC_X86_REG_EDX
from native_crypto_machine import Machine
from emulate_player_registry import PlayerRegistryMachine

class CommonRegistryMachine(PlayerRegistryMachine):
    def __init__(self):
        Machine.__init__(self)
        self.nodes={};self.version_nodes={};self.context=self.alloc(0x40)
        self.put(self.context+12,self.context+4);self.put(self.context+16,self.context+4)
        for address in (0x08978cf8,0x08978abc):
            self.uc.hook_add(UC_HOOK_CODE,self.hook,begin=address,end=address)
        self.invoke(0x0897b4ea,[self.context],count=2000000)
        self.invoke(0x08978f96,[self.context],count=2000000)
    def hook(self,u,address,size,data):
        sp=u.reg_read(UC_X86_REG_ESP)
        if address in (0x08978cf8,0x08978abc):
            context=u.reg_read(UC_X86_REG_EDX);out=u.reg_read(UC_X86_REG_EAX)
            key=self.half(self.word(self.word(sp+4)))
            nodes=self.nodes if address==0x08978cf8 else self.version_nodes
            assert context==self.context+(0 if address==0x08978cf8 else 0x1c)
            if key not in nodes:
                node=self.alloc(0x38);self.put(node+0x10,key);self.put(node+0x20,node+0x28)
                nodes[key]=node;self.rebuild_tree(nodes,context)
            self.put(out,nodes[key]);self.ret(out)
        elif address==0x081d4a40:
            target=self.word(sp+4);self.put(target,target+8);self.put(target+4,0);u.mem_write(target+8,b'\0');self.ret(target)
        else:super().hook(u,address,size,data)
    def accepts(self,request,version,reply):
        return self.invoke(0x0897aa16,[self.context,request,version,reply],count=100000)&255

if __name__=='__main__':
    m=CommonRegistryMachine()
    print('entries',len(m.nodes),'error preexisting',6 in m.nodes,'max',m.maximum_version(6))
    print('accept183',m.accepts(183,3,6),'error association',m.associations(6))
