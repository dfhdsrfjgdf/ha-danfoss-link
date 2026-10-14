"""Data coordinator for the Danfoss Link integration."""
from __future__ import annotations

import asyncio
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .danfoss import DanfossMDG

_LOGGER = logging.getLogger(__name__)


def build_device_info(coordinator: "DanfossLinkCoordinator") -> DeviceInfo:
    info = coordinator.data.get("info") or {}
    return DeviceInfo(
        identifiers={(DOMAIN, coordinator.client.cc_peer_id)},
        name=info.get("name", "Danfoss Link"),
        manufacturer="Danfoss",
        model="Link CC",
        sw_version=info.get("version"),
        serial_number=info.get("serialNo"),
    )

ENDPOINTS = {
    "info": "/api/system/info",
    "status": "/api/system/status",
    "rooms": "/api/rooms",
    "modes": "/api/modes",
    "zones": "/api/zones/living",
    "onoffdevices": "/api/onoffdevices",
    "alarms": "/api/alarms",
}


class DanfossLinkCoordinator(DataUpdateCoordinator[dict]):
    """Owns the single MDG tunnel to the CC and serialises all requests."""

    def __init__(self, hass: HomeAssistant, cert_pem: str, key_pem: str,
                 cc_peer_id: str, host: str | None = None) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=DEFAULT_SCAN_INTERVAL)
        self._client = DanfossMDG(cert_pem, key_pem, cc_peer_id, host=host)
        self._lock = asyncio.Lock()

    @property
    def client(self) -> DanfossMDG:
        return self._client

    async def _async_update_data(self) -> dict:
        try:
            return await self._run(self._fetch)
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(str(err)) from err

    async def _run(self, fn, *args):
        async with self._lock:
            return await self.hass.async_add_executor_job(fn, *args)

    def _fetch(self) -> dict:
        client = self._client
        if client.tls is None:
            client.connect()
        data: dict = {}
        for key, uri in ENDPOINTS.items():
            try:
                data[key] = client.get(uri)["content"]
            except Exception:  # noqa: BLE001
                _LOGGER.debug("Danfoss endpoint %s nepasiekiamas", uri)
                data[key] = None
        if data["rooms"] is None and data["info"] is None:
            raise RuntimeError("CC nepasiekiamas")
        return data

    async def async_request(self, uri: str, method: str, content: dict) -> dict:
        """Atlieka write ir grąžina atsakymą; atnaujina visus duomenis."""
        resp = await self._run(self._write, uri, method, content)
        await self.async_request_refresh()
        return resp

    def _write(self, uri: str, method: str, content: dict) -> dict:
        client = self._client
        try:
            if client.tls is None:
                client.connect()
            return client.request(uri, method, content=content)
        except Exception:  # noqa: BLE001
            client.close()
            client.connect()
            return client.request(uri, method, content=content)

    async def async_shutdown(self) -> None:
        await self._run(lambda: self._client.close())
