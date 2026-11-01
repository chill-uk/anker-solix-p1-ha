# Anker Solix P1 Energy Tracker for Home Assistant

> **Help validate experimental HTTP decryption:** An independent Anker SOLIX P1 firmware readout would help confirm whether the five-byte derivation value is shared across devices. Please open an issue to arrange a private exchange first. Do not attach flash dumps, keys, Wi-Fi credentials, or raw readings to a public issue. Firmware version and authentication success/failure are safe starting points.

[![GitHub release](https://img.shields.io/github/release/chill-uk/anker-solix-p1-ha?include_prereleases=&sort=semver&color=blue)](https://github.com/chill-uk/anker-solix-p1-ha/releases/)
[![issues - anker-solix-p1-ha](https://img.shields.io/github/issues/chill-uk/anker-solix-p1-ha)](https://github.com/chill-uk/anker-solix-p1-ha/issues)
[![GH-code-size](https://img.shields.io/github/languages/code-size/chill-uk/anker-solix-p1-ha?color=red)](https://github.com/chill-uk/anker-solix-p1-ha)
[![GH-last-commit](https://img.shields.io/github/last-commit/chill-uk/anker-solix-p1-ha?style=flat-square)](https://github.com/chill-uk/anker-solix-p1-ha/commits/main)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![Validation](https://github.com/chill-uk/anker-solix-p1-ha/actions/workflows/validate.yml/badge.svg)](https://github.com/chill-uk/anker-solix-p1-ha/actions/workflows/validate.yml)
![GitHub Downloads](https://img.shields.io/github/downloads/chill-uk/anker-solix-p1-ha/total)

A local-only Home Assistant custom integration for the Anker Solix P1 Energy Tracker. It reads the raw DSMR telegram from the dongle's local
HTTP endpoint.

It does **not** use the Anker's cloud API.

> [!IMPORTANT]
> This is an unofficial community integration. It is not affiliated with,
> endorsed by, connected with, or supported by Anker.

# Installation

### HACS installation

The quickest way to install this integration is via [HACS](https://github.com/hacs/integration) by clicking the button below:

[![Add to HACS via My Home Assistant](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=chill-uk&repository=anker-solix-p1-ha&category=integration)

1. Click the button above to add this repository to HACS as a custom integration.
2. Install `Anker SOLIX P1` from HACS.
3. Restart Home Assistant.
4. In Home Assistant, go to `Settings -> Devices & Services`.
5. Add the `Anker SOLIX P1` integration.

### Manual installation

1. Copy `custom_components/anker_solix_p1` into your Home Assistant config directory.
2. Restart Home Assistant.
3. In Home Assistant, add the `Anker Solix P1 Energy Tracker` integration from `Settings -> Devices & Services`.

## Polling interval

Open the integration's **Configure** dialog to:

- change its hostname or IP address;
- select a polling interval from 5 to 300 seconds;
- select single-phase or three-phase validation;
- temporarily enable telegram debug mode;
- enable encrypted diagnostic capture for support.

A changed address is probed before it is saved

## Workflow

1. Poll `http://<device-ip>/getdebugdata` at the configured interval.
2. Check the HTTP response and parse its JSON.
3. Extract the raw DSMR telegram from debugdata.
4. Validate the telegram’s CRC.
5. Parse the telegram by OBIS identifier.
6. Validate the required OBIS fields according to the manually selected single-phase or three-phase mode.
7. Convert valid measurements into Home Assistant coordinator data.
8. Update the entities while retaining previous values for optional fields that were not present in this particular telegram.
9. When a frame is invalid:
    * Debug mode enabled: immediately log the reason and redacted raw telegram, with no grace period.
    * Debug mode disabled: preserve the last valid values for up to 15 seconds; if valid data does not return, the affected entities become unavailable.

The log can distinguish between:

* HTTP or JSON failures
* Missing debugdata
* Invalid CRC
* Missing required OBIS fields
* Empty OBIS values
* Malformed values
* Unexpected units

## Experimental encrypted HTTP endpoints

Disabled by default. In the integration's **Configure** dialog, enable
**Experimental encrypted HTTP decoding**, set the host to the P1's current literal
IPv4 address, and enter your privately obtained five-byte derivation value as
10 hexadecimal digits. No firmware secret is bundled with this integration.
A hostname or IPv6 address cannot be used in this mode because derivation uses
the device's IPv4 address. Update the configured address if DHCP changes it.

This adds authenticated decoding of `/api/measurement`, `/api/wifi_info`, and
`/api/device_info` on each poll. Each response must pass AES-GCM authentication
and JSON validation. Failures are isolated from normal DSMR sensor updates;
there is no unauthenticated fallback. Endpoint field mappings remain experimental,
so decoded values do not replace existing sensor readings.

Download integration diagnostics to see per-endpoint `authenticated`,
`decode_failed`, or `request_failed` status. To obtain the decoded JSON readout,
enable **Encrypted diagnostic capture**, wait for a poll, then download diagnostics
before disabling capture or restarting Home Assistant. Endpoint JSON is included
only inside the existing encrypted support records, readable with the maintainer's
private support key. The normal diagnostics contain no derivation value or decoded
HTTP payload. Your Home Assistant configuration and backups do contain the private
derivation value; keep them private. Disable the experimental option to stop the
additional HTTP requests.

The capture retains at most 120 encrypted records for up to 10 minutes. With
experimental decoding enabled, a successful poll contributes two records, so
the record limit can be reached sooner.

## License

MIT
