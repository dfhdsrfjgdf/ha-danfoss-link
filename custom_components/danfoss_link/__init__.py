"""The Danfoss Link integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_CC_PEER_ID, CONF_CERT_PEM, CONF_HOST, CONF_KEY_PEM, DOMAIN
from .coordinator import DanfossLinkCoordinator

PLATFORMS = ["climate", "sensor", "switch", "select"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = DanfossLinkCoordinator(
        hass,
        entry.data[CONF_CERT_PEM],
        entry.data[CONF_KEY_PEM],
        entry.data[CONF_CC_PEER_ID],
        entry.data.get(CONF_HOST),
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: DanfossLinkCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_shutdown()
    return unload_ok
