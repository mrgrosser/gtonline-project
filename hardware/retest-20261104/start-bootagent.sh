#!/bin/bash

export PATH=/game/dynamic/gt-compat/bin:/usr/local/bin:/usr/bin:/bin:/usr/local/sbin:/usr/sbin:/sbin

if [ -f /game/dynamic/gt-compat/retest.enabled ]; then
    /bin/bash /game/dynamic/gt-compat/recovery-gate.sh gate
fi
exec /bin/BootAgent "$@"
