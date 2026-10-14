# Instructions for AI coding agents

This repository is an **unofficial Home Assistant integration** for Danfoss Link CC, built by reverse-engineering the Android app (`com.danfoss.linkapp`) and Trifork MDG cloud protocol.

**Human-facing setup:** [README.md](README.md) and [docs/](docs/) — do not duplicate those walkthroughs here.

**Agent-oriented documentation (read this first when changing code):**

| Document | Use when |
|----------|----------|
| [docs/agents/README.md](docs/agents/README.md) | Orientation, constraints, what not to attempt |
| [docs/agents/PROTOCOL-AND-TLS.md](docs/agents/PROTOCOL-AND-TLS.md) | MDG control/routing/cc_json, TLS quirks |
| [docs/agents/REST-API.md](docs/agents/REST-API.md) | CC HTTP API paths, write payloads, schema discovery |
| [docs/agents/CODEBASE-MAP.md](docs/agents/CODEBASE-MAP.md) | HA integration layout, threading, extension points |
| [docs/agents/DEBUGGING-PLAYBOOK.md](docs/agents/DEBUGGING-PLAYBOOK.md) | Symptom → cause → fix |
| [docs/agents/RE-SESSION-LOG-INDEX.md](docs/agents/RE-SESSION-LOG-INDEX.md) | Where full RE notes live locally (gitignored) |

## Hard constraints (do not violate)

1. **No LAN REST to the CC** — CC TCP ports were closed on tested firmware; heating API is only via cloud tunnel + `JsonWebRequest` to CC `localhost:8000`.
2. **Do not replace `tlslib.py` with OpenSSL/ssl** — server certs use **brainpoolP320r1** signatures; stock OpenSSL often cannot verify them. Custom TLS + `ecdsa` is intentional.
3. **Credentials are per app install** — `app_cert.pem`, `app_key.pem`, `cc_peer_id`; never commit real PEMs or pairings.
4. **Single active client per app cert** — phone/emulator app and HA must not connect simultaneously with the same cert.
5. **Room PATCH requires `id`** in JSON body (CC JSON Schema); partial bodies return 400 with embedded schema text.

## Default edit scope

- Production code: `custom_components/danfoss_link/**`
- User docs: `docs/*.md` (not `docs/agents/` unless updating agent specs)
- Optional local RE tree: `re/` (gitignored; may exist on maintainer machine only)

When adding features, prefer extending `DanfossLinkCoordinator.async_request()` and platform entities rather than duplicating MDG logic.
