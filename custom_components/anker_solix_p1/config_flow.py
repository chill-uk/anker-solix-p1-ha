"""Minimal config flow; verify that GET /getdebugdata contains DSMR."""
from __future__ import annotations

import ipaddress

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, OptionsFlowWithReload
from homeassistant.const import CONF_HOST
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AnkerP1Api, AnkerP1Error
from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN, MIN_SCAN_INTERVAL, MAX_SCAN_INTERVAL


def normalize_host(value: str) -> str:
    """Accept IPv4 address or DNS hostname only; never arbitrary URLs/paths."""
    host = value.strip().lower().rstrip(".")
    if not host or len(host) > 253 or any(c in host for c in (":", "/", "@", "?", "#", "\\")):
        raise ValueError("Enter a hostname or IPv4 address, without a URL or port")
    try:
        ipaddress.IPv4Address(host)
        return host
    except ipaddress.AddressValueError:
        pass
    labels = host.split(".")
    if any(not x or len(x) > 63 or x[0] == "-" or x[-1] == "-" or
           any(not (c.isascii() and (c.isalnum() or c == "-")) for c in x) for x in labels):
        raise ValueError("Invalid hostname")
    return host


class AnkerSolixP1ConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                host = normalize_host(user_input[CONF_HOST])
                await AnkerP1Api(async_get_clientsession(self.hass), host).async_get_data()
            except ValueError:
                errors["base"] = "invalid_host"
            except AnkerP1Error:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(f"host:{host}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=f"Anker SOLIX P1 ({host})", data={CONF_HOST: host})
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_HOST): str}),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return AnkerP1OptionsFlow()


class AnkerP1OptionsFlow(OptionsFlowWithReload):
    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        interval = self.config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(CONF_SCAN_INTERVAL, default=interval):
                    vol.All(vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL)),
            }),
        )
