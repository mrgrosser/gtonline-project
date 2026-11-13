#!/bin/sh
# Temporary, cabinet-only routing test. No startup/config edits.
set -eu
umask 077
IP=/sbin/ip
DEST=203.0.113.49/32
METRIC=42761
LOG=/tmp/gt-heartbeat-window.log
[ -z "$("$IP" route show table local exact "$DEST")" ] || exit 10
[ ! -e /tmp/gt-heartbeat-window.active ] || exit 11
mkdir /tmp/gt-heartbeat-window.active
SERVER=
WATCHDOG=
cleanup() {
  "$IP" route del local "$DEST" dev lo table local metric "$METRIC" 2>/dev/null || true
  [ -z "$SERVER" ] || kill "$SERVER" 2>/dev/null || true
  [ -z "$WATCHDOG" ] || kill "$WATCHDOG" 2>/dev/null || true
  rmdir /tmp/gt-heartbeat-window.active 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 1' TERM INT HUP
# Independent failsafe survives an uncatchable parent exit.
( sleep 600; "$IP" route del local "$DEST" dev lo table local metric "$METRIC" 2>/dev/null || true ) </dev/null >/tmp/gt-heartbeat-watchdog.log 2>&1 &
WATCHDOG=$!
python /tmp/cabinet_heartbeat_test.py >"$LOG" 2>&1 &
SERVER=$!
sleep 1
kill -0 "$SERVER"
grep -q '"ready": true' "$LOG"
"$IP" route add local "$DEST" dev lo table local metric "$METRIC"
echo 'Local heartbeat window active; automatic cleanup after fixture exits (maximum 10 minutes).'
wait "$SERVER"
