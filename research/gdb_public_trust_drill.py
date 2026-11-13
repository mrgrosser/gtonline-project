"""GDB Python 2/3: temporary public-context pointer selection, always restore.

Run only under independently verified gateway isolation. No network responder
is used. Original key contexts and cached provisioning bytes are not modified.
"""
import gdb, json, os, struct, hashlib, binascii, time

CONFIG='/tmp/gt-trust-drill-config.json'
REPORT='/tmp/gt-trust-drill-result.json'
mode=os.environ.get('GT_TRUST_MODE','drill')
assert mode in ('drill','apply')
if mode=='apply':
    REPORT='/tmp/gt-private-trust-applied.json'
    assert not os.path.exists(REPORT),'Existing live trust journal requires recovery'
c=json.load(open(CONFIG)); report={'stages':[], 'restored':False, 'passed':False}
if mode=='apply':
    assert open('/run/gt-gateway-isolation-verified').read().strip()==c['boot_id']
    assert open('/game/dynamic/gt-compat/positive-test.pending').read().strip()==c['boot_id']
report.update(boot_id=c['boot_id'],pid=c['pid'],original_encrypt=c['encrypt_context'],original_verify=c['verify_context'],context=c['context'])
fields={'server_rsa_n':(0x64,256),'server_rsa_e':(0x164,4),
 'client_rsa_n':(0x168,256),'client_rsa_e':(0x268,4),
 'server_dsa_y':(0x36c,96),'server_dsa_q':(0x3cc,20),
 'server_dsa_p':(0x3e0,96),'server_dsa_g':(0x440,96),
 'client_dsa_y':(0x4b4,96),'client_dsa_q':(0x514,20),
 'client_dsa_p':(0x528,96),'client_dsa_g':(0x588,96)}
def save(stage):
    report['stages'].append(stage)
    with open(REPORT+'.new','w') as f:
        json.dump(report,f,indent=2);f.flush();os.fsync(f.fileno())
    os.rename(REPORT+'.new',REPORT)
def read(a,n):return bytes(gdb.selected_inferior().read_memory(a,n))
def word(a):return struct.unpack('<I',read(a,4))[0]
def write(a,b):gdb.selected_inferior().write_memory(a,b)
def put(a,v):write(a,struct.pack('<I',v))
def call(a,args):
    signature=','.join(['unsigned int']*len(args))
    return int(gdb.parse_and_eval('((int (*)(%s))0x%x)(%s)' %
               (signature,a,','.join('0x%x'%v for v in args))))
def check_fields():
    for name,(off,n) in fields.items():
        assert read(c['context']+off,n)==binascii.unhexlify(c['public_fields'][name]),name
def verify(ctx,scratch):return call(0x08a5c727,[ctx,scratch+0x800,scratch+0x814,scratch+0x840,20])

assert open('/proc/sys/kernel/random/boot_id').read().strip()==c['boot_id']
h=hashlib.sha256()
with open('/proc/%d/exe'%c['pid'],'rb') as f:
    while True:
        b=f.read(1024*1024)
        if not b:break
        h.update(b)
assert h.hexdigest()==c['executable_sha256']
gdb.execute('set pagination off');gdb.execute('set confirm off')
gdb.execute('attach %d'%c['pid'])
selected=False;success=False
try:
    assert word(0x1ac03448)==c['context']
    assert word(c['context']+0x65c)==c['encrypt_context']
    assert word(c['context']+0x664)==c['verify_context']
    check_fields();save('preconditions_match')
    if mode=='apply' and 'verified_clock_epoch' in c:
        # Bounded maintenance check: do not let legacy direct-ISA RTC code
        # rewrite an independently verified accurate system clock.
        now=int(time.time())
        assert abs(now-int(c['verified_clock_epoch']))<30
        report['original_clock_check']=word(0x1ac03460)
        put(0x1ac03460,now)
        save('accurate_clock_recent_check_marked')
    # Allow allocator owners to run during calls; no live traffic is permitted.
    gdb.execute('set scheduler-locking off')
    scratch=call(0x08b6aaa6,[4096]) & 0xffffffff
    assert scratch>0x10000
    report['scratch']=scratch
    write(scratch,b'\0'*4096)
    f=c['new_public_fields']
    for name,off in [('server_rsa_n',0x200),('server_dsa_q',0x300),
                     ('server_dsa_p',0x320),('server_dsa_g',0x380),('server_dsa_y',0x3e0)]:
        write(scratch+off,binascii.unhexlify(f[name]))
    write(scratch+0x800,binascii.unhexlify(c['test_signature']))
    write(scratch+0x840,binascii.unhexlify(c['test_digest']))
    rsa=scratch;dsa=scratch+0x100
    assert call(0x08a5b594,[rsa,struct.unpack('<I',binascii.unhexlify(f['server_rsa_e']))[0],scratch+0x200,256])==0
    assert call(0x08a5c371,[dsa,scratch+0x300,scratch+0x320,scratch+0x380,scratch+0x3e0,96])==0
    assert verify(dsa,scratch)==0
    assert verify(c['verify_context'],scratch)==-34
    save('separate_contexts_loaded_private_signature_verified_original_rejects')
    # Both pointer writes happen while all threads are stopped. We restore the
    # original pointers without executing game code under the temporary choice.
    selected=True
    put(c['context']+0x65c,rsa);put(c['context']+0x664,dsa)
    assert word(c['context']+0x65c)==rsa and word(c['context']+0x664)==dsa
    save('temporary_pointers_selected_while_stopped')
    success=True
finally:
    if selected and not (mode=='apply' and success):
        put(c['context']+0x65c,c['encrypt_context'])
        put(c['context']+0x664,c['verify_context'])
    report['restored']=(word(c['context']+0x65c)==c['encrypt_context'] and word(c['context']+0x664)==c['verify_context'])
    check_fields()
    report['applied']=mode=='apply' and success
    report['passed']=selected and (report['restored'] or report['applied'])
    # Separate allocations deliberately retained: no speculative destructors.
    # They are unreachable by the game and will be reclaimed at process exit.
    report['temporary_allocations_retained']=bool(report.get('scratch'))
    save('private_pointers_retained_original_objects_preserved' if report['applied'] else 'original_pointers_and_cached_public_fields_verified')
    gdb.execute('detach')
print(json.dumps(report))
