"""Switch platform for Danfoss Link on/off devices."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import DanfossLinkCoordinator, build_device_info


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            async_add_entities: AddEntitiesCallback) -> None:
    coordinator: DanfossLinkCoordinator = hass.data[DOMAIN][entry.entry_id]
    devices = coordinator.data.get("onoffdevices") or []
    async_add_entities(DanfossOnOffSwitch(coordinator, d["id"]) for d in devices)


class DanfossOnOffSwitch(CoordinatorEntity[DanfossLinkCoordinator], SwitchEntity):
    def __init__(self, coordinator: DanfossLinkCoordinator, device_id: int) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_name = self._device.get("name", f"On/Off {device_id}")
        self._attr_unique_id = f"{coordinator.client.cc_peer_id}_onoff_{device_id}"
        self._attr_device_info = build_device_info(coordinator)

    @property
    def _device(self) -> dict:
        for d in self.coordinator.data.get("onoffdevices") or []:
            if d.get("id") == self._device_id:
                return d
        return {}

    @property
    def available(self) -> bool:
        return super().available and bool(self._device)

    @property
    def is_on(self) -> bool:
        return self._device.get("state") == "On"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        d = self._device
        return {
            "regulation": d.get("regulation"),
            "activity_simulation_enabled": d.get("activitySimulationEnabled"),
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._set("On")

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set("Off")

    async def _set(self, state: str) -> None:
        await self.coordinator.async_request(
            f"/api/onoffdevices/{self._device_id}", "PATCH",
            {"id": self._device_id, "state": state},
        )
