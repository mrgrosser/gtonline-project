"""Execute the staged gate's actual release loop against temporary boot/routes.
No cabinet paths, network tools, configuration, or real game launches touched.
"""
from pathlib import Path
import tempfile,subprocess,json,shlex
ROOT=Path(__file__).resolve().parent
source=(ROOT/'recovery-gate-gateway-staged.sh').read_text()
loop=source[source.index('while :; do'):source.index('\ndone',source.index('while :; do'))+5]
def run(marker,release,blackhole,local,expected,management=True):
    with tempfile.TemporaryDirectory() as td:
        base=Path(td);(base/'release').write_text(release)
        if blackhole:(base/'gateway-verified').write_text('boot-A')
        if marker is not None:(base/'positive-test.pending').write_text(marker)
        ip=base/'ip'
        ip.write_text('#!/bin/sh\ncase "$*" in\n"route show table main") '+('echo "blackhole default metric 1"' if blackhole else ':')+';;\n"route get 203.0.113.49") '+('echo "local 203.0.113.49 dev lo"' if local else 'echo "203.0.113.49 via 192.0.2.1"')+';;\n"route get 198.51.100.8") '+('echo "198.51.100.8 via 192.0.2.1 dev eth0 src 192.0.2.124"' if management else ':')+';;\nesac\n');ip.chmod(0o700)
        script='BASE='+shlex.quote(td)+'\nboot_id=boot-A\n'+loop.replace('/run/gt-retest-release',str(base/'release')).replace('/run/gt-gateway-isolation-verified',str(base/'gateway-verified')).replace('/usr/sbin/ip',str(ip)).replace('sleep 2','sleep 0.01')+'\necho RELEASED\n'
        try:
            r=subprocess.run(['bash'],input=script,text=True,capture_output=True,timeout=.2)
            allowed=r.returncode==0 and r.stdout.strip()=='RELEASED'
        except subprocess.TimeoutExpired:allowed=False
        assert allowed==expected,(marker,release,blackhole,local,allowed)
cases=[(None,'boot-A',False,False,True),(None,'boot-B',False,False,False),
 ('boot-A','boot-A',True,True,True),('boot-A','boot-A',False,True,False),
 ('boot-A','boot-A',True,False,False),('boot-B','boot-A',True,True,False),
 ('boot-A','boot-B',True,True,False),('boot-A','boot-A',True,True,False,False)]
for args in cases:run(*args)
print(json.dumps({'gate_cases_passed':len(cases),'scope':'staged actual shell loop with temporary boot/route fixtures; not installed'}))
