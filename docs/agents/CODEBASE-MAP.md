# Codebase map

## Files

```
custom_components/danfoss_link/
  __init__.py        async_setup_entry / async_unload_entry, PLATFORMS
  const.py           DOMAIN, config keys, scan interval, house-mode maps
  config_flow.py     user step; validates by connecting and GET /api/system/info
  coordinator.py     DanfossLinkCoordinator (single tunnel, poll, writes)
  climate.py         DanfossRoomClimate (1 per room)
  sensor.py          per-room temp, alarm count, system diagnostics
  select.py          DanfossHouseModeSelect (Off / AtHome / Vacation / Pause)
  switch.py          DanfossOnOffSwitch (1 per on/off device)
  strings.json       UI strings
  translations/en.json
  manifest.json      requirements: ecdsa, asn1crypto
  danfoss/
    __init__.py      re-exports DanfossMDG, HOSTS, PORT
    client.py        DanfossMDG — control + routing + cc_json (the high-level client)
    mdg.py           ControlClient + protobuf encode/parse + MT_* constants
    tlslib.py        TLS 1.2 implementation (brainpool sigs, secp256r1 ECDHE, AES-GCM)
```

The `danfoss/` package is **self-contained** (no Home Assistant imports), so it can be
used/tested standalone. `tlslib` depends only on `ecdsa` and `cryptography`; `client`
uses `asn1crypto` to parse the private key.

## Threading and connection model

- There is **one** MDG tunnel per config entry, owned by the coordinator and serialised
  with an `asyncio.Lock` (`DanfossLinkCoordinator._lock`).
- All blocking socket work runs in the executor (`hass.async_add_executor_job`).
- `_fetch()` reconnects if `client.tls is None`, then GETs the endpoints listed in
  `ENDPOINTS`. Individual endpoint failures are tolerated (value becomes `None`); if both
  `rooms` and `info` are `None`, the update fails (`UpdateFailed`).
- `_write()` retries once: on any exception it `close()`s and fully reconnects before the
  single retry.
- `async_request(uri, method, content)` performs a write then triggers a refresh.

The client lifecycle is: `connect()` control → `set_whitelist` → (per request)
`place_call` → routing handshake → TLS upgrade → send/receive cc_json.

## Data model

`coordinator.data` is a dict keyed by:

| key | endpoint |
|-----|----------|
| `info` | `/api/system/info` |
| `status` | `/api/system/status` |
| `rooms` | `/api/rooms` |
| `modes` | `/api/modes` |
| `zones` | `/api/zones/living` |
| `onoffdevices` | `/api/onoffdevices` |
| `alarms` | `/api/alarms` |

Entity platforms read from this dict via `CoordinatorEntity`.

## Entities

| Platform | Class | Unique ID suffix | Writes |
|----------|-------|------------------|--------|
| climate | `DanfossRoomClimate` | `_room_<id>` | setpoint, regulation type (preset) |
| sensor | `DanfossRoomTemperature` | `_room_<id>_temp` | — |
| sensor | `DanfossAlarmCount` | `_alarm_count` | — |
| sensor | `DanfossSystemSensor` | `_system_<key>` | — |
| select | `DanfossHouseModeSelect` | `_house_mode` | modes PUT |
| switch | `DanfossOnOffSwitch` | `_onoff_<id>` | on/off device PATCH |

All entities share one device (`build_device_info()` in `coordinator.py`, keyed by
`cc_peer_id`).

## Config entry

`entry.data` holds `cert_pem`, `key_pem`, `cc_peer_id`, and optional `host`. `cert_pem`
and `key_pem` may be **either PEM text or a filesystem path** — `client.pem_to_der()`
detects `-----BEGIN` and otherwise opens the path. `cc_peer_id` accepts colons,
underscores, or raw hex (`config_flow._normalise_peer_id`).

## Extension points

- Add an endpoint: extend `coordinator.ENDPOINTS`.
- Add a write: call `coordinator.async_request(...)`; prefer doing it from a platform
  entity so `unique_id`/`device_info` stay consistent.
- Add a platform: extend `PLATFORMS` in `__init__.py` and add a new module.

## Dependencies

`manifest.json` → `["ecdsa==0.19.2", "asn1crypto==1.5.1"]` (plus `cryptography`, provided
by HA). HA installs these on first load; a wrong version shows up in
Settings → System → Logs.
