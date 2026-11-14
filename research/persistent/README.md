# Persistent private online operation

Owner preference (2026-11-14): Golden Tee should be ONLINE unless Bob explicitly requests offline. A return to stock startup is not the intended end state.

## Service ownership

- Gateway user service `gtonline-tunnel.service`: SSH reverse forwards, restarts after disconnect, enabled under user lingering.
- Gateway user service `gtonline-online.service`: validates the exact cabinet isolation policy, verifies the cabinet clock/boot/game PID and RAM-trust readiness, then runs the private responder without a time limit. Each responder start gets a fresh private capture directory. Negotiated transport is checkpointed before reply transmission.
- Cabinet root-owned `gt-private-online/boot.sh`: invoked by the preserved BootAgent wrapper; diverts the vendor address locally before game startup and launches byte bridge/trust worker. No timed reboot or return-to-gate timer.
- Restricted root SSH command supports only status/current-boot authorization. The separate unprivileged connection supports the tunnel and server guard. Dedicated private key stays on the Gateway.
- Backend, tunnel and cabinet boot paths remain fail-closed to official service. Do not silently remove the isolation rule on failures.

## Verify after changes

Confirm enabled/active host units, fresh cabinet boot ID, bridge listeners, matching trust report PID, encrypted registration/session/sync acceptance and a fresh rendered cabinet screen. A running Python process alone is not online proof. Confirm an actual cabinet reboot and a host-service restart reconnect correctly before claiming reboot resilience. User card/login/round functionality still has separately documented protocol gaps.

## Explicit offline recovery

Only on owner's explicit request: disable the cabinet online flag first, stop host units, preserve current local player DBs and raw captures, restore/verify cabinet database and registration storage under isolation, then remove only the owned isolation policy and restore the preserved BootAgent wrapper. Do not remove isolation while private test IDs or queued test traffic remain. The private baseline, guarded SQL procedure, six storage readbacks and independently exported verification are under the private recovery backups. Do not publish those inputs.

## Failure handling

- No network: tunnel retries automatically; ordinary Internet fallback is prohibited.
- Clock mismatch: host refuses authorization; diagnose host/cabinet time before applying trust.
- Changed executable/public fields or failed GDB verification: worker stops rather than patching unknown state.
- Host restart: systemd restarts the tunnel/supervisor; same-boot encrypted transport resumes from the checkpoint when valid.
- Cabinet restart: new boot trust must be independently verified; stale session checkpoints are not reused across boots.

Private online mode is persistent infrastructure, not proof every game protocol feature has been implemented.
