from pathlib import Path
import re
p=Path(__file__).resolve().parent
s=(p/'syslog.txt').read_text()
records=re.split(r'(?=11/03/26 \d\d:\d\d:\d\d : )',s)
for start,end in [('17:38:','17:43:'),('17:44:','17:47:'),('17:48:','17:51:')]:
    text=''.join(x for x in records if x.startswith('11/03/26 ') and start<=x[9:17]<end)
    assert 'Unsupported video card GeForce GTX 1650/PCI/SSE2' in text
    assert 'StartXServerModern: layout name = layout_1280x720' in text
    assert 'XORG cannot initialize Video Card' in text
    assert 'starting DHCP lookup' not in text
    print('PASS failed boot',start,': spoof identity, modern layout request, X failure; no DHCP completion')
x=(p/'Xorg.0.log.old').read_text()
assert '17:48:07 2026' in x and 'No ServerLayout section called "layout_1280x720"' in x and 'no screens found' in x
print('PASS independent X log corroborates last failed boot')
config=(p/'xorg.conf').read_text()+(p/'05-nvidia.conf').read_text()
assert '"layout_1280x720"' not in config
assert 'Screen1920x1080x24_0x0_Dvi' in config
print('PASS missing modern layout; legacy1080p screen definitions present')
recovery=''.join(x for x in records if x.startswith('11/03/26 ') and '17:51:'<=x[9:17]<'17:52:')
assert 'StartXServer: screen name = Screen1920x1080' in recovery
assert 'IP=192.0.2.124' in recovery
assert 'Starting running of mode tree' in recovery
print('PASS recovery boot: legacy1080p, network, game mode tree')
