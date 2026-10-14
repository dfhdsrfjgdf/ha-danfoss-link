"""Select platform for Danfoss Link house mode."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MODE_ENDPOINTS, MODE_OFF, MODES
from .coordinator import DanfossLinkCoordinator, build_device_info


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            async_add_entities: AddEntitiesCallback) -> None:
    coordinator: DanfossLinkCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([DanfossHouseModeSelect(coordinator)])


class DanfossHouseModeSelect(CoordinatorEntity[DanfossLinkCoordinator], SelectEntity):
    _attr_name = "Danfoss Link Režimas"
    _attr_icon = "mdi:home-thermometer"

    def __init__(self, coordinator: DanfossLinkCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.client.cc_peer_id}_house_mode"
        self._attr_device_info = build_device_info(coordinator)

    @property
    def options(self) -> list[str]:
        return [MODE_OFF, *MODES]

    @property
    def current_option(self) -> str:
        for mode in self.coordinator.data.get("modes") or []:
            if mode.get("state") == "Active":
                return mode.get("type")
        return MODE_OFF

    async def async_select_option(self, option: str) -> None:
        if option == MODE_OFF:
            for mode in self.coordinator.data.get("modes") or []:
                if mode.get("state") == "Active":
                    await self._put(mode["type"], "Inactive")
            return
        if option == "AtHome":
            rooms = [r["id"] for r in (self.coordinator.data.get("rooms") or [])]
            await self.coordinator.async_request(
                f"/api/modes/{MODE_ENDPOINTS['AtHome']}", "PUT",
                {"type": "AtHome", "state": "Active", "rooms": rooms},
            )
            return
        await self._put(option, "Active")

    async def _put(self, mode_type: str, state: str) -> None:
        await self.coordinator.async_request(
            f"/api/modes/{MODE_ENDPOINTS[mode_type]}", "PUT",
            {"type": mode_type, "state": state},
        )
