"""Climate platform for Danfoss Link rooms."""
from __future__ import annotations

import logging

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import DanfossLinkCoordinator, build_device_info

_LOGGER = logging.getLogger(__name__)

PRESET_SCHEDULE = "Schedule"
PRESET_MANUAL = "Manual"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            async_add_entities: AddEntitiesCallback) -> None:
    coordinator: DanfossLinkCoordinator = hass.data[DOMAIN][entry.entry_id]
    rooms = coordinator.data.get("rooms") or []
    async_add_entities(DanfossRoomClimate(coordinator, room["id"]) for room in rooms)


class DanfossRoomClimate(CoordinatorEntity[DanfossLinkCoordinator], ClimateEntity):
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.HEAT]
    _attr_target_temperature_step = 0.5
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.PRESET_MODE
    )

    def __init__(self, coordinator: DanfossLinkCoordinator, room_id: int) -> None:
        super().__init__(coordinator)
        self._room_id = room_id
        self._attr_name = self._room["name"]
        self._attr_unique_id = f"{coordinator.client.cc_peer_id}_room_{room_id}"
        self._attr_device_info = build_device_info(coordinator)

    @property
    def _room(self) -> dict | None:
        for room in self.coordinator.data.get("rooms") or []:
            if room.get("id") == self._room_id:
                return room
        return None

    @property
    def available(self) -> bool:
        return super().available and self._room is not None

    @property
    def hvac_mode(self) -> HVACMode:
        return HVACMode.HEAT

    @property
    def current_temperature(self) -> float | None:
        room = self._room
        return room.get("ambientTemperature") if room else None

    @property
    def target_temperature(self) -> float | None:
        room = self._room
        if not room:
            return None
        return room.get("setpoint", {}).get("temperature")

    @property
    def min_temp(self) -> float:
        return (self._room or {}).get("minSetpoint", 6.0)

    @property
    def max_temp(self) -> float:
        return (self._room or {}).get("maxSetpoint", 35.0)

    @property
    def preset_modes(self) -> list[str]:
        return [PRESET_SCHEDULE, PRESET_MANUAL]

    @property
    def preset_mode(self) -> str | None:
        room = self._room
        return room.get("regulation", {}).get("type") if room else None

    @property
    def extra_state_attributes(self) -> dict:
        room = self._room or {}
        return {
            "zone": room.get("zone"),
            "regulation_state": room.get("regulationState"),
            "state": room.get("state"),
            "at_home_setpoint": room.get("regulation", {}).get("atHomeSetpoint"),
            "away_setpoint": room.get("regulation", {}).get("awaySetpoint"),
            "manual_setpoint": room.get("regulation", {}).get("manualSetpoint"),
        }

    async def async_set_temperature(self, **kwargs) -> None:
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is None:
            return
        await self.coordinator.async_request(
            f"/api/rooms/{self._room_id}", "PATCH",
            {"id": self._room_id, "setpoint": {"temperature": float(temp)}},
        )

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        await self.coordinator.async_request(
            f"/api/rooms/{self._room_id}", "PATCH",
            {"id": self._room_id, "regulation": {"type": preset_mode}},
        )

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        return
