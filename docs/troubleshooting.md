# Troubleshooting

## “Cannot connect” during setup

Work through this list in order.

### 1. Danfoss app still running

Only **one** client should use your app certificate at a time.

- Close Danfoss Link on the **emulator** and **phone**.
- Force-stop the app: Android **Settings → Apps → Danfoss Link → Force stop**.
- Try adding the integration again.

### 2. Wrong CC peer ID

- Re-open `SUMMARY.txt` from [pull_danfoss_creds.sh](../scripts/pull_danfoss_creds.sh) or check the pairing file for `["peer_id"]=`.
- If you have **multiple** CCs paired, use the peer ID for the controller you want (one integration entry per CC).

### 3. Wrong or incomplete PEM text

- Certificate and key must include the full blocks:

  ```text
  -----BEGIN CERTIFICATE-----
  ...
  -----END CERTIFICATE-----
  ```

  ```text
  -----BEGIN EC PRIVATE KEY-----
  ...
  -----END EC PRIVATE KEY-----
  ```

- If you pasted into HA, ensure no extra spaces or missing lines.
- Prefer **file paths** under `/config/...` if paste fails.

### 4. Credentials from an old pairing

If you **factory-reset the CC** or **paired again** in the app, old PEM files no longer work. Export credentials again ([getting-credentials.md](getting-credentials.md)).

### 5. Internet / cloud

Home Assistant needs outbound **HTTPS (443)** to Danfoss MDG servers. Blocked firewalls or DNS filters can cause failures.

### 6. Dependencies

On first load, HA installs Python packages from `manifest.json` (`ecdsa`, `asn1crypto`). Check **Settings → System → Logs** for pip errors if the integration fails to load at all.

---

## Integration loads but entities are unavailable

- Wait one full poll cycle (~30 s).
- **Settings → Devices & services → Danfoss Link → Reload**.
- Check logs for `CC nepasiekiamas` / connection errors — often the same “second client connected” issue.

---

## Emulator: app cannot find CC

- PC and CC on the **same home network** (same VLAN).
- Try disabling VPN on the PC.
- Confirm the official app works on a normal phone on Wi‑Fi first — then repeat pairing on the emulator.

---

## `adb root` / script fails on a physical phone

Non-rooted phones cannot read `/data/data/...`. Use the **emulator method** in [getting-credentials.md](getting-credentials.md).

---

## `adb: device unauthorized`

On the phone, accept the **USB debugging** RSA fingerprint dialog. Run `adb devices` again.

---

## Still stuck?

Collect (redact PEMs before sharing):

- Home Assistant log lines containing `danfoss_link`
- Whether Danfoss app works on the same network
- HA install type (OS, Docker, etc.)

Open an issue on the project GitHub with that information.
