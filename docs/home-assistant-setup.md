# Home Assistant setup

This guide assumes you already exported **`app_cert.pem`**, **`app_key.pem`**, and your
**CC peer ID** — see **[Getting credentials](getting-credentials.md)**.

## Requirements

- Home Assistant (OS, Supervised, Container, or Core) with outbound HTTPS to the internet
- The three credential values above
- The Danfoss Link app **not** connected at the same time (close the phone app, stop the emulator)

> **Version:** requires Home Assistant **2023.5** or newer.

---

## Step 1 — Install the integration

### Option A — HACS (recommended for updates)

1. Make sure [HACS](https://hacs.xyz/) is installed.
2. **HACS → Integrations → ⋮ (top right) → Custom repositories**.
3. Add the repository URL, category **Integration**, and click **Add**.
4. Search for **Danfoss Link** in HACS and click **Download**.
5. **Restart Home Assistant**.

### Option B — Manual copy (works everywhere)

Home Assistant loads custom integrations from `config/custom_components/<name>/`:

| Install type | Where `config` lives |
|--------------|----------------------|
| HA OS / Supervised | Use **File editor**, **Samba**, or **Studio Code Server** add-on |
| Docker | The folder you mounted as `/config` |
| Core (venv) | Your YAML directory (often `~/.homeassistant`) |

Copy this entire folder from the repository into `config/custom_components/`:

```text
custom_components/danfoss_link/
```

You should end up with:

```text
config/
  custom_components/
    danfoss_link/
      __init__.py
      manifest.json
      climate.py
      ...
      danfoss/
        client.py
        ...
```

Then **Restart Home Assistant**. On first load HA installs the Python dependencies from
`manifest.json` (`ecdsa`, `asn1crypto`); wait for the restart to finish.

---

## Step 2 — Store credentials on the HA machine (recommended)

Using file paths is easier than pasting large PEM blocks into the UI. Create a folder only
your user can read:

```text
config/danfoss_link_creds/
  app_cert.pem
  app_key.pem
```

Copy the two PEM files from your PC (SCP, Samba, USB, etc.). Then lock down permissions
(SSH / Terminal add-on):

```bash
chmod 700 /config/danfoss_link_creds
chmod 644 /config/danfoss_link_creds/app_cert.pem
chmod 600 /config/danfoss_link_creds/app_key.pem
```

Keep the **CC peer ID** in a password manager or a small note **outside** git.
Do **not** put PEM files inside `custom_components`.

---

## Step 3 — Add the integration

1. **Settings → Devices & services**
2. Bottom right: **Add integration**
3. Search: **Danfoss Link**
4. Fill in the form:

   | Field | What to enter |
   |-------|----------------|
   | App certificate | Either paste the **full PEM text** (with `BEGIN`/`END` lines) **or** a path HA can read, e.g. `/config/danfoss_link_creds/app_cert.pem` |
   | App private key | Same — paste or path to `app_key.pem` |
   | CC peer ID | From the pairing file (colons, underscores, or continuous hex all work) |
   | MDG host | **Leave empty** unless support told you to use a specific server |

5. Submit. The integration connects to the cloud, opens a tunnel to your CC, and reads
   `/api/system/info` to verify access.

If validation succeeds, the integration is titled with your system name (from
`/api/system/info`) and entities are created. If you see **“Cannot connect”**, see
[troubleshooting.md](troubleshooting.md).

---

## What appears in Home Assistant

| Platform | What you get |
|----------|----------------|
| **Climate** | One entity per **room** — current temperature, target setpoint, preset Schedule/Manual |
| **Select** | House mode (`Off` / At home / Vacation / Pause) |
| **Switch** | On/off devices reported by the CC (none on some systems) |
| **Sensor** | Per-room ambient temperature, alarm count, and diagnostics (version, uptime) |

Updates poll the cloud roughly every **30 seconds** (`cloud_polling`).

---

## Daily use

1. **Stop using the Danfoss app** on the phone/emulator that shares the **same**
   certificate, or HA may fail to connect intermittently (one client per cert).
2. You can uninstall the app from the emulator after export; **keep backups** of the two
   PEM files and the peer ID.
3. After a **CC factory reset** or **new pairing** in the app, export **new** credentials
   and reconfigure the integration (existing entry → **Configure/Reconfigure**).
4. Test one room manually from the UI before building automations that write setpoints.

---

## Updating the integration

- **HACS:** HACS shows an update when a new release is published; click **Update**, then
  **Restart Home Assistant**.
- **Manual:** replace `config/custom_components/danfoss_link/` with the new version, then
  restart.
- Check release notes for config-flow or entity changes.

---

## Next

- [troubleshooting.md](troubleshooting.md) — connection problems
- [security.md](security.md) — protecting your private key
