set -e
[ -f /game/dynamic/gt-compat/retest.enabled ]
sha256sum -c /game/dynamic/gt-compat/rollback-retest-20261104/unchanged.sha256
sync
nohup /bin/bash -c 'sleep 3; /sbin/shutdown -h now' </dev/null >/tmp/gt-shutdown.log 2>&1 &
echo 'ORDERLY_POWEROFF_REQUESTED'
