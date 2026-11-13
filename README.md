# Golden Tee Online Project

An engineering journal for a private Golden Tee online-service emulator and eventual card-based player login.

## Follow the project

Read **[the project log](PROJECT_LOG.md)** for the dated change history, experiments, verified results, recovery work, and next steps.

## Current milestone — November 13, 2026

- Private registration and encrypted session establishment accepted in an isolated cabinet test.
- Follow-up synchronization and acknowledgments accepted; a green LIVE indicator observed.
- Online-menu access, card swipe, player login, and saved profiles **not yet verified end to end**.
- Original registration state restored after testing; no permanent private service installed.

This repository contains the project journal and **122 sanitized source/dependency files**, including protocol scripts, native emulation harnesses, recovery tools, tests, and earlier GPU/SSH work. It is not a ready-to-install emulator or a connection to official online services.

Read **[the source guide](SOURCE_GUIDE.md)** before running anything: some historical test scripts perform live operations, and many modules require private inputs that are intentionally not included. The guide distinguishes standalone checks from tests requiring private research inputs.

Credentials, private keys, identifying cabinet details, captures, and proprietary binaries are not included.

Meaningful future changes and verification results will be recorded in the project log.

## Latest offline progress

Method2 decompression is implemented and checked against original routines using synthetic inputs. Eight new standalone compression tests pass; live compatibility remains unverified. See [compression findings](COMPRESSION_NOTES.md) and the [player-login research plan](PLAYER_LOGIN_PLAN.md). No cabinet changes were made for this step.

The [offline player/profile store](PLAYER_STORE.md) now supports explicit enrollment, keyed identity lookup, revisioned saves and durable retry receipts. Fifteen tests pass, including concurrency and interrupted-save recovery. This component is not yet connected to cabinet login; no player-facing success is claimed.

The latest [V2 codec and correlation checks](PLAYER_V2_CODEC.md) bring the selected offline suite to **87 passing methods**, including **37 standalone methods**. Request183/reply184 versions0–3 now have strict payload codecs. The network responder still refuses player login; no database commit or on-screen login is proven.

Six further native queue tests exercise missing-context errors and successful synthetic request correlation. Selected coverage is now93 methods; actual SQL and live login remain unverified.
