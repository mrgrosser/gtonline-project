#!/bin/bash
# Temporary controlled-test gate. Uses the cabinet's native DHCP configuration.
BASE=/game/dynamic/gt-compat
LOG=$BASE/recovery-test.log
network_ready() {
    /usr/sbin/ip -4 -o addr show dev eth0 scope global | /bin/grep -q ' inet '
}
ensure_access() {
    if ! network_ready; then
        /usr/bin/timeout 135 /etc/rc.d/it.d/ethernet start
    fi
    if ! /usr/sbin/ss -lnt | /bin/grep -q ':22 '; then
        /usr/sbin/sshd
    fi
    /usr/sbin/ip -4 addr show dev eth0
    /usr/sbin/ss -lnt | /bin/grep ':22 '
    network_ready
}
case "${1:-gate}" in
    check)
        ensure_access
        exit $?
        ;;
    delayed-check)
        sleep 90
        { date; echo 'One-shot post-launch recovery check'; ensure_access; } >> "$LOG" 2>&1
        exit $?
        ;;
    gate) ;;
    *) exit 2 ;;
esac
[ -f "$BASE/retest.enabled" ] || exit 0
boot_id=$(/bin/cat /proc/sys/kernel/random/boot_id)
{
    date
    echo "Recovery gate entered: $boot_id"
    ensure_access
    echo 'Game held; waiting for this boot ID in /run/gt-retest-release'
} >> "$LOG" 2>&1
# Missing/failed networking never releases the game automatically.
while :; do
    release=$(/bin/cat /run/gt-retest-release 2>/dev/null)
    if [ "$release" = "$boot_id" ]; then
        if [ ! -e "$BASE/positive-test.pending" ]; then
            break
        fi
        # Pending registration experiment: release only its originally armed boot,
        # with host-verified gateway isolation and vendor redirection ready.
        armed_boot=$(/bin/cat "$BASE/positive-test.pending" 2>/dev/null)
        if [ "$armed_boot" = "$boot_id" ] &&
           [ "$(/bin/cat /run/gt-gateway-isolation-verified 2>/dev/null)" = "$boot_id" ] &&
           /usr/sbin/ip route get 203.0.113.49 | /bin/grep -q '^local 203.0.113.49 ' &&
           /usr/sbin/ip route get 198.51.100.8 | /bin/grep -q '^198.51.100.8 via 192.0.2.1 dev eth0 '; then
            break
        fi
    fi
    sleep 2
done
/usr/bin/nohup /bin/bash "$BASE/recovery-gate.sh" delayed-check </dev/null >> "$LOG" 2>&1 &
echo "Game released: $boot_id" >> "$LOG"
exit 0
