# Anker SOLIX P1 — Home Assistant

Local-only Home Assistant integration for the Anker SOLIX P1 energy meter.

## Transport

**Only** `GET http://<host>/getdebugdata` is called. The endpoint returns JSON with a `debugdata` DSMR P1 telegram and optional `timeout_times`, `crc_error_times` and `total_times` counters.

No cloud connection, authentication, EcoFlow-specific endpoint, binary Anker endpoint, or device-control request is used.

## Install

Install as a HACS custom repository (Integration), or copy `custom_components/anker_solix_p1` to Home Assistant's custom_components directory. Restart Home Assistant. Add **Anker SOLIX P1** under Settings → Devices & services and enter the device's LAN IP/hostname.

Initial polling interval is 10 seconds, configurable from 5–300 seconds.

## Sensors

Electricity tariff counters, instantaneous import/export, phase voltage/current/power (only when present in the telegram), M-Bus gas/heat meter volume/energy (when present), and DSMR-reception counters.

Note: device diagnostics and meter identifiers should not be logged publicly. The integration does not currently verify the optional DSMR CRC. Sensor creation for optional OBIS/M-Bus fields occurs at setup based on the first valid telegram.

The parser and sensor layout adapt the general Home Assistant/DSMR architecture of [EcoFlow P1 HA](https://github.com/chill-uk/ecoflow-p1-ha), **without using its transport endpoints or vendor-specific protocols**.
