"""Sensor platform for Danfoss Link."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import DanfossLinkCoordinator, build_device_info


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            async_add_entities: AddEntitiesCallback) -> None:
    coordinator: DanfossLinkCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = []
    for room in coordinator.data.get("rooms") or []:
        if room.get("hasTemperatureSensor", True):
            entities.append(DanfossRoomTemperature(coordinator, room["id"]))
    entities.append(DanfossAlarmCount(coordinator))
    entities.append(DanfossSystemSensor(coordinator, "version", "Versija"))
    entities.append(DanfossSystemSensor(coordinator, "uptime", "Uptime"))
    async_add_entities(entities)


class DanfossRoomTemperature(CoordinatorEntity[DanfossLinkCoordinator], SensorEntity):
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, coordinator: DanfossLinkCoordinator, room_id: int) -> None:
        super().__init__(coordinator)
        self._room_id = room_id
        self._attr_name = f"{self._room.get('name', room_id)} Temperatūra"
        self._attr_unique_id = f"{coordinator.client.cc_peer_id}_room_{room_id}_temp"
        self._attr_device_info = build_device_info(coordinator)

    @property
    def _room(self) -> dict:
        for room in self.coordinator.data.get("rooms") or []:
            if room.get("id") == self._room_id:
                return room
        return {}

    @property
    def native_value(self) -> float | None:
        return self._room.get("ambientTemperature")


class DanfossAlarmCount(CoordinatorEntity[DanfossLinkCoordinator], SensorEntity):
    _attr_name = "Danfoss Link Aliarmai"
    _attr_icon = "mdi:alert"

    def __init__(self, coordinator: DanfossLinkCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.client.cc_peer_id}_alarm_count"
        self._attr_device_info = build_device_info(coordinator)

    @property
    def native_value(self) -> int:
        return len(self.coordinator.data.get("alarms") or [])

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "alarms": [
                {
                    "id": a.get("id"),
                    "level": a.get("level"),
                    "room": a.get("room"),
                    "node": a.get("node"),
                    "is_read": a.get("isRead"),
                }
                for a in (self.coordinator.data.get("alarms") or [])
            ]
        }


class DanfossSystemSensor(CoordinatorEntity[DanfossLinkCoordinator], SensorEntity):
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: DanfossLinkCoordinator, key: str, name: str) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_name = f"Danfoss Link {name}"
        self._attr_unique_id = f"{coordinator.client.cc_peer_id}_system_{key}"
        self._attr_device_info = build_device_info(coordinator)

    @property
    def native_value(self) -> str | None:
        return (self.coordinator.data.get("info") or {}).get(self._key)
