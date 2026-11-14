#!/bin/bash
set -eu
BASE=/game/dynamic/gt-private-online
[ -f "$BASE/enabled" ] || exit 0
# Always divert the vendor endpoint locally before allowing game launch.
/usr/sbin/ip route get 63.116.120.49 | /bin/grep -q '^local 63.116.120.49 ' || /usr/sbin/ip route add local 63.116.120.49/32 dev lo table local metric 42761
if ! /usr/sbin/ss -lnt | /bin/grep -q ':22 '; then /usr/sbin/sshd; fi
alive() {
    [ -f "$1" ] || return 1
    process=$(cat "$1")
    [ -r "/proc/$process/cmdline" ] && tr '\0' ' ' < "/proc/$process/cmdline" | grep -Fq "$2"
}
if ! alive /run/gt-private-bridge.pid "$BASE/cabinet_relay_bridge.py"; then
    nohup python -u "$BASE/cabinet_relay_bridge.py" --persistent </dev/null >> "$BASE/bridge.log" 2>&1 &
    echo $! > /run/gt-private-bridge.pid
fi
if ! alive /run/gt-private-worker.pid "$BASE/cabinet-worker.py"; then
    nohup python -u "$BASE/cabinet-worker.py" </dev/null >> "$BASE/worker.log" 2>&1 &
    echo $! > /run/gt-private-worker.pid
fi
