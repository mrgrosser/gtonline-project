set -e
cat /sys/bus/pci/devices/0000:01:00.0/vendor /sys/bus/pci/devices/0000:01:00.0/device
sha256sum -c /game/dynamic/gt-compat/rollback-retest-20261104/unchanged.sha256
bash -n /game/dynamic/gt-compat/bin/cat
cat /game/dynamic/gt-compat/bin/cat
dmesg | grep -E 'NVRM|nvidia|Xid' | tail -15
