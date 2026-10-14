"""Constants for the Danfoss Link integration."""
from __future__ import annotations

from datetime import timedelta

DOMAIN = "danfoss_link"

CONF_CERT_PEM = "cert_pem"
CONF_KEY_PEM = "key_pem"
CONF_CC_PEER_ID = "cc_peer_id"
CONF_HOST = "host"

DEFAULT_SCAN_INTERVAL = timedelta(seconds=30)
DEFAULT_TIMEOUT = 30

# House modes (order matters for the select entity)
MODE_OFF = "Off"
MODES = ["AtHome", "Vacation", "Pause"]
MODE_ENDPOINTS = {"AtHome": "athome", "Vacation": "vacation", "Pause": "pause"}
