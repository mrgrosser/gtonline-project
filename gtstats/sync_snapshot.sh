#!/usr/bin/env bash
set -euo pipefail
: "${GT_WORKSPACE:?Set GT_WORKSPACE}" "${GT_STATS_HOST:?Set GT_STATS_HOST}"
cd "$GT_WORKSPACE"
exec 9>gtstats/.sync.lock
flock -n 9 || exit 0
python3 gtstats/export_snapshot.py --data .private-gtonline-player --imports .private-livewire --courses gtstats/courses.json --output gtstats/.runtime/stats.json
scp -q -o BatchMode=yes -o ConnectTimeout=8 gtstats/.runtime/stats.json "$GT_STATS_HOST:/opt/gtstats/data/stats.pending.json"
ssh -o BatchMode=yes -o ConnectTimeout=8 "$GT_STATS_HOST" 'chmod 644 /opt/gtstats/data/stats.pending.json && mv /opt/gtstats/data/stats.pending.json /opt/gtstats/data/stats.json'
