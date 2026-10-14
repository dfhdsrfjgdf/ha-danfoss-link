# Protocol and TLS

This is the distilled result of the reverse-engineering effort (Android app + captured
network traffic). It is the reference for the vendored client in
`custom_components/danfoss_link/danfoss/`.

## 1. Layered picture

The app reaches the CC in four steps:

```
1. CONTROL   app ─mTLS─► MDG control server         (peer registry, place_call)
2. ROUTING   app ──────► MDG routing server          (token, then TLS upgrade)
3. TLS       app ◄═mTLS═► CC  (through the tunnel)   (end-to-end with the CC)
4. cc_json   app ═══════► CC's own HTTP API          (JsonWebRequest to localhost:8000)
```

The HA integration mirrors this exactly in the `DanfossMDG` class.

## 2. TCP framing (all layers)

Every frame is prefixed with a **2-byte big-endian length** (`packet = 2`, `>H`). The
first byte of a control/routing frame is a **type code**, followed by a protobuf body.

```
[ uint16 length ][ uint8 type_code ][ protobuf payload ]
        length counts the type code + protobuf
```

## 3. CONTROL layer

Transport: raw TLS 1.2 (mTLS) to an MDG control host, SNI
`mdg-danfoss.hosted.trifork.com`.

**Handshake** (type `MT_HANDSHAKE = 1`):

| field | value |
|-------|-------|
| `magic` (fixed32, field 1) | `0xf09d8ca8` |
| `version_major` (field 2) | `1` |
| `version_minor` (field 3) | `0` |
| properties (field 4) | **omitted** for `auto_connect` (no properties at all) |

**Message type codes**

| code | message |
|------|---------|
| 1 | `MT_HANDSHAKE` |
| 2 | `MT_BYE` |
| 3 | `MT_RECONNECT` |
| 4 | `MT_PING` |
| 5 | `MT_PING_REPLY` |
| 10 | `MT_PLACE_CALL` |
| 11 | `MT_PLACE_CALL_REPLY` |
| 12 | `MT_INCOMING_CALL` |
| 13 | `MT_INCOMING_CALL_REPLY` |
| 20 | `MT_SET_PEER_WHITELIST` |
| 21 | `MT_SET_PEER_WHITELIST_REPLY` |
| 30/31 | `MT_ALLOCATE_PAIRING_CHANNEL` (+ reply) |
| 32/33 | `MT_PLACE_PAIRING_CALL` (+ reply) |

**Call flow used by HA**

1. `set_whitelist([cc_peer_id])` → wait for `SET_PEER_WHITELIST_REPLY`.
2. `place_call(cc_peer_id, protocol="cc_json")` → `PLACE_CALL_REPLY`.

`PLACE_CALL_REPLY` fields: `req_id`(1), `result`(2), `routing`(3), `result_text`(4).
`PLACE_CALL_RESULT`: `OK=0`, `PEER_NOT_AVAILABLE`, `SERVER_ERROR`.
`routing` contains `peer_name`(3), `router`(4) = repeated `{host(1), port(2)}`,
`token`(5, bytes).

## 4. ROUTING layer

Connect to the `routing.router[].host:port` returned by `place_call` and send a routing
handshake (type `RMT_HANDSHAKE = 0`):

| field | value |
|-------|-------|
| `magic` (fixed32, field 1) | `0xf09d8c95` |
| `version_major` / `version_minor` | `1` / `0` |
| `token` (bytes, field 4) | token from `place_call_reply` |
| `supported_protocols` (field 5) | `"tlsv1_2"` |

Routing type codes: `RMT_HANDSHAKE=0`, `PLEASEHOLD=1`, `GOAHEAD=2`, `ROUTINGERROR=3`.
Wait for `GOAHEAD=2`; on `ROUTINGERROR=3` abort. Then **upgrade the same socket to TLS**
(mTLS, end-to-end with the CC).

## 5. cc_json layer

On the post-GOAHEAD TLS socket, send length-prefixed JSON:

**Request (app → CC)**

```json
{
  "id": 42,
  "data": {
    "type": "JsonWebRequest",
    "data": {
      "uri": "/api/rooms/0",
      "method": "PATCH",
      "headers": ["Accept: application/json; charset=utf-8"],
      "port": 8000,
      "content": { "id": 0, "setpoint": { "temperature": 21.0 } }
    }
  }
}
```

The CC forwards the request to its own `http://127.0.0.1:8000<uri>`.

**Response (CC → app)**

```json
{
  "id": 42,
  "cc_time": 1791893185000,
  "data": {
    "type": "JsonWebResponse",
    "data": { "headers": [], "status": 200, "statusDescription": "OK", "content": { ... } }
  }
}
```

There is a `cc_json-flow-control` mechanism with capacity 17; the simple client sends one
request and reads one response (synchronous), which stays well within the window.

## 6. TLS quirks (the important part)

The cloud/CC certificates and the app identity use **brainpoolP320r1** with **explicit
EC parameters**. This is why a stock TLS stack fails and a custom one exists.

- **Certificate signatures**: brainpoolP320r1 (via `ecdsa`). OpenSSL 3.6, LibreSSL, and
  Python's `ssl` cannot be relied upon to verify these; `ecdsa` can.
- **ECDHE key exchange group**: standard **`secp256r1`** (`0x0017`), curve type `3`
  (named), uncompressed point (65 bytes).
- **Cipher suite negotiated**: **`0xC02C`** (`TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256`).
- **Server Key Exchange** signature algorithm: **`0x0603` = ECDSA + SHA-512** (not
  SHA-256). The client must pick the hash from `sig_alg` when verifying the SKE.
- **No `extended_master_secret`** — the server does not negotiate it (server hello only
  carries `0x000B` `ec_point_formats` and `0xFF01` `renegotiation_info`).
- **`CertificateRequest`** is sent → **mTLS is mandatory** (present `app_cert.pem`).
- **GCM records** use an explicit nonce: `nonce = fixed_iv(4) + explicit(8)`, AAD = the
  sequence number, with an all-zero record sequence as used by this server.

### ClientHello profile (`app_profile`)

The app sends a specific, minimal ClientHello for the routing/TLS upgrade. Reproducing it
avoids a fatal `handshake_failure` alert (`02 28`) that the server otherwise sends:

- record version `0x0301` for the ClientHello record;
- extensions only: `0x000b` (`ec_point_formats` `03 00 01 02`), `0x000a`
  (`supported_groups` `0017 001d 0019 001c 001b 0018 001a 0016 000e 000d 000b 000c 0009 000a`),
  `0x000d` (`signature_algorithms`, all), `0x000f` (heartbeat), `0x0015` (padding ~250 bytes);
- **no** `renegotiation_info`, `extended_master_secret`, `signature_algorithms_cert`, or SNI.

`tlslib.TLS12` exposes `app_profile = True` to emit this exact ClientHello.

### Multi-message records

LibreSSL-based peers can pack several handshake messages into one TLS record. The reader
must keep a dedicated handshake buffer (`hs_buf`) across records, otherwise a leftover
message corrupts parsing. This is already handled in `tlslib._read_handshake`.

## 7. Hosts

MDG is a load-balanced cluster; any of these may serve control, and the routing host comes
from `place_call_reply`:

```
77.66.11.90:443   77.66.11.92:443   5.179.92.180:443   5.179.92.182:443
```

Control SNI: `mdg-danfoss.hosted.trifork.com`. Routing/TLS upgrade uses an empty SNI.

> The app's bundled config hardcodes `5.179.92.180/182`, but at runtime it uses the whole
> cluster. The client tries hosts in turn until control connects.

## 8. Registration note

`app_cert.pem` / `app_key.pem` are the app's **cloud identity**, registered during
pairing. They keep working after the emulator/phone is shut down, as long as the pairing
is not removed on the CC or the app is not re-paired (which regenerates them).
