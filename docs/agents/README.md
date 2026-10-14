# Agent orientation — Danfoss Link HA integration

You are looking at an **unofficial Home Assistant integration** for the Danfoss Link
central controller (CC). It was built by **reverse engineering** the Android app
`com.danfoss.linkapp` and the Trifork **MDG** cloud protocol. There is **no public
API**.

Read this file first, then the topic files in the table below.

## What the integration does

Home Assistant impersonates the phone app: it connects to the Danfoss cloud with the
app's **client certificate**, opens a tunnel to the CC, and speaks the same JSON-over-tunnel
API the app uses (`/api/rooms`, `/api/modes`, …). It then exposes `climate`, `sensor`,
`select`, and `switch` entities and lets HA write settings back.

```
Home Assistant ──mTLS──► MDG control ──place_call──► MDG routing ──mTLS──► CC ──► zones/rooms
```

## Where things are

| Path | Purpose |
|------|---------|
| `custom_components/danfoss_link/` | The integration (production code) |
| `custom_components/danfoss_link/danfoss/` | Vendored, self-contained MDG/TLS client |
| `docs/` | Human-facing documentation |
| `docs/agents/` | This agent documentation |
| `scripts/pull_danfoss_creds.sh` | Export credentials from emulator/rooted phone |

## Topic files

| Document | Use when |
|----------|----------|
| [PROTOCOL-AND-TLS.md](PROTOCOL-AND-TLS.md) | MDG control/routing/cc_json layers, framing, TLS quirks |
| [REST-API.md](REST-API.md) | CC HTTP API paths, write payloads, JSON-Schema discovery |
| [CODEBASE-MAP.md](CODEBASE-MAP.md) | Integration layout, threading, data model, extension points |
| [DEBUGGING-PLAYBOOK.md](DEBUGGING-PLAYBOOK.md) | Symptom → cause → fix |
| [RE-SESSION-LOG-INDEX.md](RE-SESSION-LOG-INDEX.md) | Where the full RE notes live locally (gitignored) |

## Hard constraints (do not violate)

1. **No LAN REST to the CC.** Tested firmware has all CC TCP ports closed. Heating data
   is only reachable via the cloud tunnel (`JsonWebRequest` to CC `localhost:8000`).
2. **Do not replace `danfoss/tlslib.py` with `ssl`/OpenSSL.** Server/certificate
   signatures use **brainpoolP320r1**, which stock OpenSSL often cannot verify. The
   custom TLS + `ecdsa` path is intentional (see PROTOCOL-AND-TLS.md).
3. **Credentials are per app install**: `app_cert.pem`, `app_key.pem`, and the CC
   `cc_peer_id`. Never commit real PEMs or pairings.
4. **One active client per certificate.** The phone/emulator app and HA must not connect
   at the same time with the same certificate; the cloud rejects the second session.
5. **Room `PATCH` requires `id`** in the JSON body (the CC validates against a JSON
   Schema; partial bodies return `400` that embeds the schema text).

## Quick start for an agent

```bash
# Syntax-check the integration without Home Assistant installed
python -m py_compile custom_components/danfoss_link/*.py \
  custom_components/danfoss_link/danfoss/*.py

# Talk to a real CC using the vendored client (no HA needed)
python - <<'PY'
import sys; sys.path.insert(0, "custom_components/danfoss_link")
from danfoss import DanfossMDG
with DanfossMDG("app_cert.pem", "app_key.pem", "e7:af:e3:...") as cc:
    print(cc.get("/api/system/info")["content"])
PY
```

Dependencies for the client: `ecdsa`, `asn1crypto` (see `manifest.json`), plus
`cryptography` (bundled with Home Assistant).

## Editing scope

- Production code: `custom_components/danfoss_link/**`
- Human docs: `docs/*.md`
- Agent docs: `docs/agents/*.md`

Prefer extending `DanfossLinkCoordinator.async_request()` and the platform entities
rather than duplicating MDG logic.
