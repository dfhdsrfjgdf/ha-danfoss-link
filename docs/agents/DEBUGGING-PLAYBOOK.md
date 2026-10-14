# Debugging playbook

Symptom → likely cause → fix. See also [REST-API.md](REST-API.md) and
[PROTOCOL-AND-TLS.md](PROTOCOL-AND-TLS.md).

## `cannot_connect` in the config flow

| Cause | How to confirm | Fix |
|-------|----------------|-----|
| Another client holds the certificate | Danfoss app/emulator is connected | Force-stop the app, stop the emulator, retry |
| Wrong CC peer ID | Pairing file `["peer_id"]=…` | Re-copy; one entry per CC |
| PEM text truncated / wrong block | `-----BEGIN …-----` missing | Use file paths under `/config`, or paste full PEM |
| Credentials from an old pairing | CC factory-reset or re-paired | Re-export credentials |
| No outbound 443 | firewall/DNS filter | Allow HA → `*.hosted.trifork.com`, `77.66.11.x`, `5.179.92.x` |
| Missing Python deps | Logs show pip error for `ecdsa`/`asn1crypto` | Check Settings → System → Logs |

The config flow validates by connecting and reading `/api/system/info`; a failure here is
almost always identity (cert/peer) or “second client”.

## Integration loads but entities are unavailable

- Wait one poll cycle (~30 s), then **Reload** the entry.
- Look for `CC nepasiekiamas` / connection errors — usually the second-client issue.
- Confirm `/api/rooms` works with the standalone client (below).

## Control (setpoint / mode) returns 400

The CC rejected the JSON body against its schema. Common mistakes:

- Room `PATCH` **without `id`** → schema error. Always include `"id": <id>`.
- `PUT /api/modes/athome` **without a non-empty `rooms` array** → schema error.
- `PATCH /api/zones/...` **without `name`** → schema error.
- Sending unknown keys (`additionalProperties: false`).

Read the schema in `errorMessages` and match it exactly.

## TLS failure right after connecting (fatal `handshake_failure`, alert `02 28`)

- The server expects the **app_profile ClientHello**. Ensure `tls.app_profile = True`
  before `handshake()` for the routing/TLS-upgrade connection.
- Do **not** swap `tlslib` for `ssl` — brainpool signatures are unsupported and the
  ClientHello differs.

## Handshake parse errors / corruption

- A record can contain **multiple handshake messages**; keep the `hs_buf` logic.
- SKE verification must use the hash from `sig_alg` (`0x0603` = ECDSA-SHA512).

## Emulator credential export

- `adb root` works on emulators/rooted devices only.
- If the script says “luadata not found”, open the app once, wait for rooms to load, rerun.
- Wrong emulator ABI (x86) → the app’s native libs won’t run; use **arm64-v8a**.

## Standalone smoke test (no Home Assistant)

```bash
python - <<'PY'
import sys; sys.path.insert(0, "custom_components/danfoss_link")
from danfoss import DanfossMDG
cert, key = "/config/danfoss_link_creds/app_cert.pem", "/config/danfoss_link_creds/app_key.pem"
ccid = "e7:af:e3:77:61:90:0d:b5:1f:87:d9:7c:ea:da:10:1e:25:26:9b:a1"
with DanfossMDG(cert, key, ccid) as cc:
    print(cc.get("/api/system/info")["content"])
    print([ (r["id"], r["name"], r["ambientTemperature"]) for r in cc.get("/api/rooms")["content"] ])
PY
```

If this works but HA does not, the problem is in HA (identity conflict, deps, or entry
data) rather than the protocol.

## Collecting evidence for an issue

- HA log lines containing `danfoss_link`
- Whether the official app works on the same network
- HA install type and version
- **Redact** certificates and private keys before posting.
