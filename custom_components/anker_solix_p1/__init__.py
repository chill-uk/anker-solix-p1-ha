"""Local-only Anker SOLIX P1 Home Assistant integration."""
from __future__ import annotations

from homeassistant.const import CONF_HOST
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AnkerP1Api
from .const import PLATFORMS
from .coordinator import AnkerP1Coordinator


async def async_setup_entry(hass, entry) -> bool:
    api = AnkerP1Api(async_get_clientsession(hass), entry.data[CONF_HOST])
    coordinator = AnkerP1Coordinator(hass, entry, api)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass, entry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
