# Golden Tee Online Project

An engineering journal for a private Golden Tee online-service emulator and eventual card-based player login.

## Follow the project

Read **[the project log](PROJECT_LOG.md)** for the dated change history, experiments, verified results, recovery work, and next steps.

## Current milestone — November 13, 2026 (evening)

- Physical card login and local profile replies demonstrated on the cabinet.
- A complete 18-hole round persisted locally and reopened; native statistics projection prepared and served.
- Local Home Edition equipment selections persist; no official purchases or wallet operations.
- User confirmed course entry after fixing partial/cached setup requests.
- Still experimental: contest-result request coverage, end-of-round equipment uploads, automatic completed-history collection and Great Shot Points behavior remain incomplete or under investigation.
- Testing uses a bounded, isolated session with temporary memory/network changes; this is not a persistent drop-in installation.

This repository contains **204 sanitized source/dependency files**. Private captures, credentials, player databases and proprietary binaries are excluded.

**Helping stabilize it? Start with [CONTRIBUTING.md](CONTRIBUTING.md).**

Read **[the source guide](SOURCE_GUIDE.md)** before running anything: some historical test scripts perform live operations, and many modules require private inputs that are intentionally not included. The guide distinguishes standalone checks from tests requiring private research inputs.

Credentials, private keys, identifying cabinet details, captures, and proprietary binaries are not included.

Meaningful future changes and verification results will be recorded in the project log.

## Latest offline progress

Method2 decompression is implemented and checked against original routines using synthetic inputs. Eight new standalone compression tests pass; live compatibility remains unverified. See [compression findings](COMPRESSION_NOTES.md) and the [player-login research plan](PLAYER_LOGIN_PLAN.md). No cabinet changes were made for this step.

The [offline player/profile store](PLAYER_STORE.md) now supports explicit enrollment, keyed identity lookup, revisioned saves and durable retry receipts. Fifteen tests pass, including concurrency and interrupted-save recovery. This component is not yet connected to cabinet login; no player-facing success is claimed.

The latest [V2 codec and correlation checks](PLAYER_V2_CODEC.md) bring the selected offline suite to **87 passing methods**, including **37 standalone methods**. Request183/reply184 versions0–3 now have strict payload codecs. The network responder still refuses player login; no database commit or on-screen login is proven.

Six further native queue tests exercise missing-context errors and successful synthetic request correlation. Selected coverage is now93 methods; actual SQL and live login remain unverified.

Nighthawk queue-error and caller status-gate checks bring selected offline coverage to97 methods. Partial request context after a failed lookup is explicitly tested; no live-login claim is made.

ITNet completion-reader and polling coverage brings the selected offline suite to110 methods. Polling exit is not login success; see [completion and cabinet acceptance boundaries](PLAYER_HANDOFF.md#itnet-completion-versus-player-login-success). Player-specific routing investigation continues.
