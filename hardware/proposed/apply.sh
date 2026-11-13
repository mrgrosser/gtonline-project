#!/bin/bash
set -euo pipefail
base=/opt/gtonline-analysis/review-20261103
stage="$base/proposed"
root=/mnt/gt-review-root
serial=$(lsblk -dn -o SERIAL /dev/sdb | xargs)
[[ "$serial" = REPLACE_WITH_VERIFIED_SSD_SERIAL ]] || { echo 'SSD identity mismatch'; exit 1; }
[[ -z "$(lsblk -n -o MOUNTPOINTS /dev/sdb | tr -d '[:space:]')" ]] || { echo 'SSD has mounted filesystems'; exit 1; }
[[ -d /opt/gtonline-analysis/backups/goldentee-original ]] || exit 1
mkdir -p "$root"
mount -o ro,noload /dev/sdb4 "$root"
trap 'umount "$root" 2>/dev/null || true; blockdev --setro /dev/sdb' EXIT
cmp "$root/etc/rc.d/samba" "$base/extracted/etc/rc.d/samba"
cmp "$root/etc/rc.d/it.d/it" "$base/extracted/etc/rc.d/it.d/it"
bash -n "$stage/samba"
bash -n "$stage/it"
backup="$base/rollback-ssh-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -m 700 "$backup"
cp -a "$root/etc/rc.d/samba" "$backup/samba"
cp -a "$root/etc/rc.d/it.d/it" "$backup/it"
sha256sum "$backup/samba" "$backup/it" > "$backup/SHA256SUMS"
net_before=$(sha256sum "$root/etc/rc.d/it.d/ifconfig.eth0" | cut -d' ' -f1)
umount "$root"
blockdev --setrw /dev/sdb
blockdev --setrw /dev/sdb4
mount -o rw /dev/sdb4 "$root"
cp -a "$root/etc/rc.d/samba" "$root/etc/rc.d/samba.jarvis-pre-ssh-20261103"
cp -a "$root/etc/rc.d/it.d/it" "$root/etc/rc.d/it.d/it.jarvis-pre-ssh-20261103"
cat "$stage/samba" > "$root/etc/rc.d/samba"
cat "$stage/it" > "$root/etc/rc.d/it.d/it"
bash -n "$root/etc/rc.d/samba"
bash -n "$root/etc/rc.d/it.d/it"
cmp "$stage/samba" "$root/etc/rc.d/samba"
cmp "$stage/it" "$root/etc/rc.d/it.d/it"
[[ "$net_before" = "$(sha256sum "$root/etc/rc.d/it.d/ifconfig.eth0" | cut -d' ' -f1)" ]]
stat -c '%a %u:%g %n' "$root/etc/rc.d/samba" "$root/etc/rc.d/it.d/it"
sync
umount "$root"
blockdev --setro /dev/sdb
trap - EXIT
lsblk -o NAME,SERIAL,RO,MOUNTPOINTS /dev/sdb
printf 'VERIFIED: two edits applied; Ethernet config unchanged; SSD unmounted. Rollback: %s\n' "$backup"
