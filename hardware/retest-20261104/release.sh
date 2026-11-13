set -e
[ -f /game/dynamic/gt-compat/retest.enabled ]
pgrep -f '^/bin/bash /game/dynamic/gt-compat/recovery-gate.sh gate$'
/bin/cat /proc/sys/kernel/random/boot_id > /run/gt-retest-release
cat /run/gt-retest-release
