"""Anker SOLIX P1 Energy Tracker integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AnkerP1Api
from .const import PLATFORMS
from .coordinator import AnkerP1Coordinator


@dataclass(slots=True)
class AnkerP1RuntimeData:
    """Runtime data for an Anker SOLIX P1 config entry."""

    coordinator: AnkerP1Coordinator


type AnkerP1ConfigEntry = ConfigEntry[AnkerP1RuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: AnkerP1ConfigEntry) -> bool:
    """Set up Anker SOLIX P1 from a config entry."""
    host = entry.options.get(CONF_HOST, entry.data[CONF_HOST])
    api = AnkerP1Api(async_get_clientsession(hass), host)
    coordinator = AnkerP1Coordinator(hass, entry, api)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = AnkerP1RuntimeData(coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: AnkerP1ConfigEntry) -> bool:
    """Unload an Anker SOLIX P1 config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        entry.runtime_data.coordinator.encrypted_capture.clear()
    return unloaded
