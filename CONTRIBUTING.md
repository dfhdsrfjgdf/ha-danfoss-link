# Contributing

Thanks for helping improve the Danfoss Link integration.

## Ground rules

- **Never commit secrets.** No `app_cert.pem`, `app_key.pem`, pairing files, peer IDs,
  APKs, or decompiled sources. `.gitignore` already blocks the common ones.
- **Respect the hard constraints** in [AGENTS.md](AGENTS.md) — especially: no LAN REST to
  the CC, and do not replace the vendored TLS stack with OpenSSL/`ssl`.
- Changing heating settings affects real homes. Be conservative with writes.

## Development setup

There is no build step. The integration is pure Python and the `danfoss/` client is
self-contained.

```bash
# Syntax check everything
python -m py_compile custom_components/danfoss_link/*.py \
  custom_components/danfoss_link/danfoss/*.py

# (Optional) run the client standalone if you have credentials
pip install ecdsa asn1crypto cryptography
```

To test inside Home Assistant, copy `custom_components/danfoss_link/` into a dev HA
instance's `config/custom_components/` and restart, or use
[`hass` / a dev container](https://developers.home-assistant.io/docs/development_environment/).

## CI

Two GitHub Actions validate every push and PR:

- **Hassfest** — manifest/integration structure
- **HACS** — HACS repository structure

Run them locally with [`hassfest`](https://github.com/home-assistant/actions) if you want
to catch issues before pushing.

## Pull requests

1. Keep the change focused; one topic per PR.
2. Update docs when behaviour changes:
   - user-facing → `README.md` / `docs/`
   - protocol or REST → `docs/agents/PROTOCOL-AND-TLS.md` / `docs/agents/REST-API.md`
   - internals → `docs/agents/CODEBASE-MAP.md`
3. Add an entry to [CHANGELOG.md](CHANGELOG.md) under **Unreleased**.
4. Fill in the PR template checklist.

## Reporting bugs

Use the issue templates. Include HA version, integration version, install type, the
failing step, and redacted logs (`danfoss_link` in Settings → System → Logs). **Redact
certificates and keys.**

## License

By contributing you agree your work is released under the [MIT License](LICENSE).
