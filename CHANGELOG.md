# Changelog

All notable changes to this project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-10-14

### Added

- Initial public release.
- Home Assistant custom integration `danfoss_link` (cloud, `iot_class: cloud_polling`).
- Config flow accepting PEM text **or** file paths plus the CC peer ID.
- Platforms:
  - `climate` — one entity per room (current temperature, target setpoint, Schedule/Manual preset).
  - `sensor` — per-room ambient temperature, alarm count, and diagnostic sensors (version, uptime).
  - `select` — house mode (`Off`, `AtHome`, `Vacation`, `Pause`).
  - `switch` — on/off devices reported by the CC.
- Vendored, self-contained MDG/cc_json client with a custom TLS 1.2 stack (works around
  brainpoolP320r1 certificate signatures).
- `scripts/pull_danfoss_creds.sh` to export credentials from an Android emulator / rooted phone.
- Documentation for humans (`docs/`) and AI agents (`docs/agents/`).

[0.1.0]: https://github.com/dfhdsrfjgdf/ha-danfoss-link/releases/tag/v0.1.0
