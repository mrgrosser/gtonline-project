set -e
uptime
ps -ef | grep -E 'BootAgent|/tmp/go|dhcpcd|recovery-gate' | grep -v grep
cat /proc/driver/nvidia/gpus/*/information
DISPLAY=:0 /usr/bin/xrandr --current | head -18
tail -60 /game/dynamic/syslog/syslog.txt
tail -16 /game/dynamic/gt-compat/recovery-test.log
