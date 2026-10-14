# Danfoss Link for Home Assistant

[![Hassfest](https://github.com/dfhdsrfjgdf/ha-danfoss-link/actions/workflows/hassfest.yaml/badge.svg)](https://github.com/dfhdsrfjgdf/ha-danfoss-link/actions/workflows/hassfest.yaml)
[![HACS](https://github.com/dfhdsrfjgdf/ha-danfoss-link/actions/workflows/hacs.yaml/badge.svg)](https://github.com/dfhdsrfjgdf/ha-danfoss-link/actions/workflows/hacs.yaml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Unofficial [Home Assistant](https://www.home-assistant.io/) custom integration for
**Danfoss Link** central controllers (CC). It reads room temperatures, setpoints, house
modes, and on/off devices, and lets you control them from Home Assistant.

> **Not affiliated with Danfoss or Trifork.** Use at your own risk. Changing heating
> settings affects your real home.

## How it works (in plain language)

The Danfoss Link **phone app** does not talk to your CC over plain Wi‑Fi HTTP on your LAN.
Instead it:

1. Connects to Danfoss **cloud** servers (MDG) with a **client certificate**.
2. Opens a secure **tunnel** to your CC.
3. Sends normal heating API calls (`/api/rooms`, etc.) through that tunnel.

Home Assistant uses the **same certificates** as the app, so the cloud treats HA like
"the app." You do **not** need the CC's IP address or open ports on the CC.

```text
  Home Assistant  ──►  Danfoss cloud (MDG)  ──►  your Link CC  ──►  thermostats / valves
        uses app_cert.pem + app_key.pem + CC peer ID
```

See [docs/architecture.md](docs/architecture.md) for the technical picture.

## What you need before you start

| Item | Why |
|------|-----|
| A working **Danfoss Link** system with a **CC** already set up | HA controls what the app would control |
| **Three secrets** from the Android app (see below) | Cloud login identity |
| Home Assistant with **custom components** enabled (any normal install) | To load this integration |
| About **30–60 minutes** the first time | Mostly one-time credential export |

The three values for Home Assistant:

1. **App certificate** (`app_cert.pem` text)
2. **App private key** (`app_key.pem` text) — treat like a password
3. **CC peer ID** — looks like `e7:af:e3:77:61:90:...` (20 bytes with colons)

## Recommended path: Android emulator (easiest for most HA users)

If your phone is not rooted, the **simplest reliable method** is a one-time setup on a
**PC or Mac** with the Android emulator, pair the app there, then copy the credential
files off the emulator.

**Full walkthrough:** [docs/getting-credentials.md](docs/getting-credentials.md)

**Quick version after pairing:**

1. Install [Android Studio](https://developer.android.com/studio) and create an **arm64**
   virtual phone with **Google Play**.
2. Install **Danfoss Link** from the Play Store and **pair with your CC** (same Wi‑Fi as
   the CC).
3. Run our helper script (with the emulator running):

   ```bash
   cd scripts
   ./pull_danfoss_creds.sh ~/danfoss_link_creds
   ```

4. Use the printed **CC peer ID** and the two PEM files when adding the integration.

You can **shut down the emulator** after export; the certificates keep working in Home
Assistant. Do **not** run the Danfoss app and HA **at the same time** (same identity).

**Alternative:** rooted Android phone + `adb` — same script, see the doc.

## Install the integration

### HACS (recommended)

1. **HACS → Integrations → ⋮ → Custom repositories**.
2. Add this repository URL with category **Integration**.
3. Search for **Danfoss Link**, then **Download**.
4. **Restart Home Assistant**.

### Manual

1. Copy the folder `custom_components/danfoss_link` into your HA
   `config/custom_components/` directory.
2. Restart Home Assistant.

Then go to **Settings → Devices & services → Add integration** → search **Danfoss Link**
and enter your **cert**, **key**, and **CC peer ID** (leave MDG host blank). Entities appear
within a minute. Full guide: [docs/home-assistant-setup.md](docs/home-assistant-setup.md).

## Documentation

| Document | Contents |
|----------|----------|
| [docs/getting-credentials.md](docs/getting-credentials.md) | Emulator setup, pairing, scripts, peer ID |
| [docs/home-assistant-setup.md](docs/home-assistant-setup.md) | Install (HACS/manual), config flow, entities |
| [docs/troubleshooting.md](docs/troubleshooting.md) | `cannot_connect`, conflicts, updates |
| [docs/security.md](docs/security.md) | Backups, who can access your keys |
| [docs/architecture.md](docs/architecture.md) | Technical overview |
| [AGENTS.md](AGENTS.md) | For AI coding agents / contributors |
| [docs/agents/](docs/agents/) | Protocol, REST API, codebase map, debugging |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Never commit certificates or keys.

## License

MIT — see [LICENSE](LICENSE). Danfoss Link and related names are trademarks of their owners.
