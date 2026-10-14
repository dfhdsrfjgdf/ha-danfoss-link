# Architecture

A high-level view for developers and curious users. Deep protocol details live in
[agents/PROTOCOL-AND-TLS.md](agents/PROTOCOL-AND-TLS.md) and
[agents/REST-API.md](agents/REST-API.md).

## Big picture

The Danfoss Link Android app does not talk to the CC over the LAN. It authenticates to
Danfoss's **Trifork MDG** cloud with a per-install **client certificate**, asks the cloud
to open a tunnel to the CC, and then speaks the CC's HTTP JSON API through it. This
integration impersonates that app.

```text
 Home Assistant                              Danfoss cloud (Trifork MDG)
 ┌───────────────┐   mTLS    ┌──────────┐   control (place_call)   ┌───────────┐
 │ danfoss_link  │ ────────► │ control  │ ───────────────────────► │  router   │
 │ coordinator   │           └──────────┘                          └─────┬─────┘
 │   + platforms │   mTLS (routing handshake → TLS upgrade)            │
 └───────┬───────┘ ◄═══════════════════════════════════════════════════╝
         │  cc_json (JsonWebRequest)
         ▼
   ┌───────────────────────────┐
   │  Danfoss Link CC (tunnel) │  http://127.0.0.1:8000  /api/rooms, /api/modes …
   └───────────────────────────┘
```

## Layers

| Layer | Responsibility | Code |
|-------|----------------|------|
| control | Connect to MDG, register peer, `place_call` to get a tunnel token | `danfoss/mdg.py`, `danfoss/client.py` |
| routing | Exchange the token for a `GOAHEAD`, then upgrade the socket to end-to-end TLS | `danfoss/client.py` |
| TLS | Custom TLS 1.2 (brainpool certificate signatures, `secp256r1` ECDHE, AES-128-GCM) | `danfoss/tlslib.py` |
| cc_json | Length-prefixed JSON `JsonWebRequest` → CC `localhost:8000` | `danfoss/client.py` |
| integration | Poll loop, entity platforms, config flow | `custom_components/danfoss_link/` |

## Home Assistant side

- **Config flow** validates the credentials by connecting and reading `/api/system/info`.
- **`DanfossLinkCoordinator`** owns a single tunnel, serialised with an `asyncio.Lock`;
  blocking I/O runs in HA's executor. It polls the CC every ~30 s and exposes the data to
  entities.
- **Platforms** map CC data to entities:

  | Platform | Entity |
  |----------|--------|
  | `climate` | one per room — current temp, target setpoint, Schedule/Manual preset |
  | `select` | house mode (`Off` / AtHome / Vacation / Pause) |
  | `sensor` | room temperature, alarm count, diagnostics |
  | `switch` | on/off devices |

Writes go through `DanfossLinkCoordinator.async_request()` and trigger a refresh.

See [agents/CODEBASE-MAP.md](agents/CODEBASE-MAP.md) for file-by-file detail.
