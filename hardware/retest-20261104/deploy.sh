set -e
BASE=/game/dynamic/gt-compat
BACKUP=$BASE/rollback-retest-20261104
[ "$(hostname)" = example-cabinet ]
[ ! -e "$BACKUP" ]
[ ! -e "$BASE/bin/cat" ]
[ ! -e "$BASE/retest.enabled" ]
printf '%s  %s\n' '2e1579d18f4e805e888cf8e940c166379a3bb9eeab0c4825985e3a3c9350a5d4' /etc/rc.d/it.d/install_nvidia | sha256sum -c -
printf '%s  %s\n' '344ad58edf6085ff7f81e23125cc39a966a7f4adead69191bf3bdc006705889f' /etc/rc.d/it.d/ethernet | sha256sum -c -
mkdir -m 700 "$BACKUP"
cp -p "$BASE/start-bootagent.sh" "$BACKUP/start-bootagent.sh"
cp -p /etc/inittab /etc/rc.d/it.d/ethernet /etc/rc.d/it.d/ifconfig.eth0 /etc/rc.d/it.d/install_nvidia "$BACKUP/"
sha256sum /etc/inittab /etc/rc.d/it.d/ethernet /etc/rc.d/it.d/ifconfig.eth0 /etc/rc.d/it.d/install_nvidia > "$BACKUP/unchanged.sha256"
cat > "$BASE/recovery-gate.sh.new" <<'GT_PUBLIC_PAYLOAD'
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
    [ "$release" = "$boot_id" ] && break
    sleep 2
done
/usr/bin/nohup /bin/bash "$BASE/recovery-gate.sh" delayed-check </dev/null >> "$LOG" 2>&1 &
echo "Game released: $boot_id" >> "$LOG"
exit 0
GT_PUBLIC_PAYLOAD
bash -n "$BASE/recovery-gate.sh.new"
printf "%s  %s\n" 78027f7ab7887af639bd9f9beb0058bcc9a094cf2663d6530d2922d44d896657 "$BASE/recovery-gate.sh.new" | sha256sum -c -
chmod 755 "$BASE/recovery-gate.sh.new"
chown root:root "$BASE/recovery-gate.sh.new"
mv "$BASE/recovery-gate.sh.new" "$BASE/recovery-gate.sh"
cat > "$BASE/bin/cat.new" <<'GT_PUBLIC_PAYLOAD'
#!/bin/bash
# Game-only GTX1080 -> generic 750 Ti profile. Never mask driver setup.
# Test candidate: gameplay, display and audio still require physical verification.
if [ "$#" -eq 1 ] && [ "$1" = /proc/bus/pci/devices ]; then
    ancestor=$PPID
    for depth in 1 2 3 4; do
        ancestor_exe=$(/usr/bin/readlink "/proc/$ancestor/exe" 2>/dev/null)
        case "$ancestor_exe" in
            '/tmp/go'|'/tmp/go (deleted)')
                /bin/cat "$1" | /bin/sed 's/\t10de1b80\t/\t10de1380\t/'
                exit ${PIPESTATUS[0]}
                ;;
        esac
        parent=0
        while read -r key value rest; do
            if [ "$key" = 'PPid:' ]; then parent=$value; break; fi
        done < "/proc/$ancestor/status" 2>/dev/null
        [ "$parent" -gt 1 ] 2>/dev/null || break
        ancestor=$parent
    done
fi
exec /bin/cat "$@"
GT_PUBLIC_PAYLOAD
bash -n "$BASE/bin/cat.new"
printf "%s  %s\n" 496b5a126d20eedf824092466eace1ec1403d34a41e2a0f194bb4ac4dd5bb33f "$BASE/bin/cat.new" | sha256sum -c -
chmod 755 "$BASE/bin/cat.new"
chown root:root "$BASE/bin/cat.new"
mv "$BASE/bin/cat.new" "$BASE/bin/cat"
cat > "$BASE/start-bootagent.sh.new" <<'GT_PUBLIC_PAYLOAD'
#!/bin/bash

export PATH=/game/dynamic/gt-compat/bin:/usr/local/bin:/usr/bin:/bin:/usr/local/sbin:/usr/sbin:/sbin

if [ -f /game/dynamic/gt-compat/retest.enabled ]; then
    /bin/bash /game/dynamic/gt-compat/recovery-gate.sh gate
fi
exec /bin/BootAgent "$@"
GT_PUBLIC_PAYLOAD
bash -n "$BASE/start-bootagent.sh.new"
printf "%s  %s\n" 58b3e98da560331e7c4b62e8fffe23e465c4d47791b8fb48eded087fe5faca89 "$BASE/start-bootagent.sh.new" | sha256sum -c -
chmod 755 "$BASE/start-bootagent.sh.new"
chown root:root "$BASE/start-bootagent.sh.new"
mv "$BASE/start-bootagent.sh.new" "$BASE/start-bootagent.sh"
/bin/bash "$BASE/recovery-gate.sh" check
cmp <(/bin/cat /proc/bus/pci/devices) <("$BASE/bin/cat" /proc/bus/pci/devices)
sha256sum -c "$BACKUP/unchanged.sha256"
touch "$BASE/retest.enabled"
sync
echo 'PREPARATION_DEPLOYED_AND_ARMED'
