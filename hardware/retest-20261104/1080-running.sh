set -e
uptime
ps -p 1908 -o pid,etime,stat,args
tail -40 /game/dynamic/syslog/syslog.txt
dmesg | grep -E 'NVRM: Xid|RmInitAdapter|GPU has fallen' || true
cat /proc/asound/pcm
cat /proc/asound/card*/pcm*p/sub*/status
