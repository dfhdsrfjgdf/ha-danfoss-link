# Security and privacy

## What the private key is

`app_key.pem` is the **private half** of your Danfoss Link app identity. Anyone with this key and certificate can talk to your heating system **as your app** through Danfoss cloud (same as someone using your phone with the app open).

Treat it like a **password**:

- Do not email it, post it in forums, or commit it to Git.
- Restrict file permissions on HA (`chmod 600` on PEM files where possible).
- Prefer HA **Secrets** or a restricted folder under `/config` only admins can read.

## Backups

Back up:

- `app_cert.pem`
- `app_key.pem`
- CC peer ID (text note)

Store backups encrypted (password manager, encrypted USB, vault). If you lose them, you must repeat the emulator/phone export after pairing.

## Cloud dependency

This integration uses **Danfoss cloud** (`iot_class: cloud_polling`). If Danfoss changes servers or disables access, the integration may stop working until updated.

There is **no official public API** documented by Danfoss for this path; the integration is community reverse-engineering.

## Unofficial software disclaimer

Not endorsed by Danfoss. You are responsible for testing setpoints and modes in your home.
