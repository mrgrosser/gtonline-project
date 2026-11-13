from pathlib import Path
import subprocess,tempfile,os,time
root=Path(__file__).resolve().parent
with tempfile.TemporaryDirectory(prefix='gt-retest-') as td:
    t=Path(td)
    def executable(name,text):
        p=t/name;p.write_text('#!/bin/bash\n'+text);p.chmod(0o700);return str(p)
    fixture='0100\t10de1b80\t0\n0101\t10de10f0\t0\n'
    f=t/'pci';f.write_text(fixture)
    cat=executable('cat',f'if [ "$1" = /proc/bus/pci/devices ]; then exec /bin/cat {f}; fi\nexec /bin/cat "$@"\n')
    readlink=executable('readlink','echo "/tmp/go (deleted)"\n')
    source=(root/'cat').read_text().replace('/bin/cat',cat)
    candidate=t/'shim';candidate.write_text(source.replace('/usr/bin/readlink',readlink))
    out=subprocess.check_output(['bash',str(candidate),'/proc/bus/pci/devices'],text=True)
    assert out==fixture.replace('10de1b80','10de1380');print('PASS game-context GPU-only substitution; audio unchanged')
    candidate.write_text(source)
    assert subprocess.check_output(['bash',str(candidate),'/proc/bus/pci/devices'],text=True)==fixture
    print('PASS non-game PCI query stays native')
    assert subprocess.check_output(['bash',str(candidate),str(f)],text=True)==fixture
    print('PASS ordinary file reads unchanged')
    candidate.write_text(source.replace('/usr/bin/readlink',readlink))
    f.write_text(fixture.replace('10de1b80','10de1380'))
    assert subprocess.check_output(['bash',str(candidate),'/proc/bus/pci/devices'],text=True)==f.read_text()
    print('PASS physical 750 Ti input unchanged')
    base=t/'base';base.mkdir()
    calls=t/'calls'
    ip=executable('ip','echo "2: eth0 inet 192.0.2.124/24 scope global eth0"\n')
    ss=executable('ss','echo "LISTEN 0 128 0.0.0.0:22 0.0.0.0:*"\n')
    forbidden=executable('forbidden',f'echo unexpected >> {calls}; exit 99\n')
    nohup=executable('nohup','exit 0\n')
    gate=(root/'recovery-gate.sh').read_text().replace('/game/dynamic/gt-compat',str(base)).replace('/usr/sbin/ip',ip).replace('/usr/sbin/sshd',forbidden).replace('/usr/sbin/ss',ss).replace('/etc/rc.d/it.d/ethernet',forbidden).replace('/usr/bin/nohup',nohup).replace('/run/gt-retest-release',str(t/'release'))
    g=t/'gate';g.write_text(gate)
    subprocess.run(['bash',str(g),'check'],check=True,stdout=subprocess.DEVNULL)
    assert not calls.exists();print('PASS healthy network check does not restart DHCP/SSH')
    subprocess.run(['bash',str(g),'gate'],check=True,timeout=3)
    print('PASS unarmed gate returns immediately')
    (base/'retest.enabled').touch()
    p=subprocess.Popen(['bash',str(g),'gate'])
    try:
        time.sleep(.3);assert p.poll() is None
        (t/'release').write_text('wrong-boot-id\n');time.sleep(2.1);assert p.poll() is None
        print('PASS armed gate blocks missing/stale release')
        (t/'release').write_text(Path('/proc/sys/kernel/random/boot_id').read_text())
        assert p.wait(timeout=4)==0
        print('PASS current boot ID releases the gate')
    finally:
        if p.poll() is None:p.terminate();p.wait()
