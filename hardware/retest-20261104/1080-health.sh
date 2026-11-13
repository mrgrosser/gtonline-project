set -e
uptime
ps -p 1908 -o pid,etime,stat,args
dmesg | grep -E 'NVRM|Xid' | tail -18
tail -50 /var/log/Xorg.0.log
tail -20 /game/dynamic/gt-compat/recovery-test.log
DISPLAY=:0 /usr/bin/nvidia-settings -q GPUCoreTemp -q GPUUtilization -t 2>/dev/null || true
