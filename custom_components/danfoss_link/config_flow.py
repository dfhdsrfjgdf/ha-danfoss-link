"""Config flow for the Danfoss Link integration."""
from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from .const import (
    CONF_CC_PEER_ID,
    CONF_CERT_PEM,
    CONF_HOST,
    CONF_KEY_PEM,
    DOMAIN,
)
from .danfoss import DanfossMDG

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CERT_PEM): str,
        vol.Required(CONF_KEY_PEM): str,
        vol.Required(CONF_CC_PEER_ID): str,
        vol.Optional(CONF_HOST): str,
    }
)


def _normalise_peer_id(value: str) -> str:
    value = value.strip()
    if ":" in value:
        return value
    value = value.replace("_", "").replace(" ", "")
    return ":".join(value[i:i + 2] for i in range(0, len(value), 2))


async def _validate(hass: HomeAssistant, data: dict) -> dict:
    peer_id = _normalise_peer_id(data[CONF_CC_PEER_ID])

    def _probe():
        client = DanfossMDG(
            data[CONF_CERT_PEM],
            data[CONF_KEY_PEM],
            peer_id,
            host=data.get(CONF_HOST) or None,
        )
        try:
            client.connect()
            info = client.get("/api/system/info")["content"]
            return info
        finally:
            client.close()

    info = await hass.async_add_executor_job(_probe)
    return {"title": info.get("name", "Danfoss Link"), "peer_id": peer_id}


class DanfossLinkConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                result = await _validate(self.hass, user_input)
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Danfoss Link validation failed")
                errors["base"] = "cannot_connect"
            else:
                user_input[CONF_CC_PEER_ID] = result["peer_id"]
                await self.async_set_unique_id(result["peer_id"])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=result["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )
