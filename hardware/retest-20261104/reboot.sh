set -e
[ -f /game/dynamic/gt-compat/retest.enabled ]
/sbin/shutdown -r +1 'Controlled recovery gate test with 750 Ti'
