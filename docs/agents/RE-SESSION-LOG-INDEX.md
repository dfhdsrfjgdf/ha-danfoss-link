# Reverse-engineering log index (local only)

The full reverse-engineering workspace is **not published** — it contains extracted
credentials, the APK, emulator images, and decompiled sources. It lives **outside** this
repository (typically `../re/` relative to the repo root on the maintainer's machine) and
is covered by `.gitignore`. This page indexes it so an agent can find material **if it has
access**.

> If you are an external contributor without that directory: everything needed to work on
> the integration is in this repo. The published docs already distil the protocol.

## Layout (maintainer machine)

| Path | Contents | Use for |
|------|----------|---------|
| `re/tls/tlslib.py` | Original prototype TLS 1.2 stack | Reference for `danfoss/tlslib.py` |
| `re/tls/mdg.py` | Original control/routing protobuf client | Reference for `danfoss/mdg.py` |
| `re/tls/danfoss.py` | Original high-level `DanfossMDG` | Reference for `danfoss/client.py` |
| `re/pulled/luadata/app_cert.pem` | Exported app certificate | Live testing (never commit) |
| `re/pulled/luadata/app_key.pem` | Exported app private key | Live testing (never commit) |
| `re/pulled/luadata/pairings/<peer>` | CC peer-ID pairing files | Copying `cc_peer_id` |
| `re/jadx/` (or similar) | jadx decompilation of `com.danfoss.linkapp` | Finding request classes, schema hints |
| `re/*.apk` | The Danfoss Link APK | Re-decompiling |
| `re/venv/` | Python venv with `ecdsa`, `cryptography`, `asn1crypto`, `paramiko` | Running probes |
| `session*.md` (repo root) | Exported AI session logs from the RE effort | Full narrative history |
| `*.pcapng` | Captured cloud traffic | Re-checking framing/TLS |

## High-value findings (already captured in these docs)

| Finding | Documented in |
|---------|---------------|
| Control/routing/cc_json layers, magic numbers, message codes | [PROTOCOL-AND-TLS.md](PROTOCOL-AND-TLS.md) |
| TLS quirks (brainpool sigs, secp256r1 ECDHE, `0xC02C`, SKE SHA-512, app_profile) | [PROTOCOL-AND-TLS.md](PROTOCOL-AND-TLS.md) |
| CC HTTP endpoints and exact write schemas | [REST-API.md](REST-API.md) |
| Integration internals | [CODEBASE-MAP.md](CODEBASE-MAP.md) |
| Symptom → fix | [DEBUGGING-PLAYBOOK.md](DEBUGGING-PLAYBOOK.md) |

## Extracting request classes from the APK (reproducible)

The app's cc_json request classes live under `com.danfoss.cumulus.comm.req.*`. A quick
jadx search for `JsonWebRequest` / `api/rooms` / `setpoint` surfaces the exact payloads
and confirms the schemas in [REST-API.md](REST-API.md).

## Reminder

Never copy anything from `re/` that contains **keys, certificates, pairing files, or the
APK** into this repository. The published integration only needs the three credential
*values*, which the user supplies at runtime.
