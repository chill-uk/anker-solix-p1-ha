"""Polling coordinator for one local GET endpoint."""
from __future__ import annotations

from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AnkerP1Api, AnkerP1Data, AnkerP1Error
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, CONF_SCAN_INTERVAL


class AnkerP1Coordinator(DataUpdateCoordinator[AnkerP1Data]):
    def __init__(self, hass, entry, api: AnkerP1Api) -> None:
        super().__init__(
            hass, __import__("logging").getLogger(__name__),
            name=DOMAIN, config_entry=entry,
            update_interval=timedelta(seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)),
        )
        self.api = api

    async def _async_update_data(self) -> AnkerP1Data:
        try:
            return await self.api.async_get_data()
        except AnkerP1Error as err:
            raise UpdateFailed(str(err)) from err
