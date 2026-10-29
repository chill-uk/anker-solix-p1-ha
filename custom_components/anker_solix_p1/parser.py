"""DSMR OBIS extraction based on the EcoFlow P1 integration's parsing model.

Preserves raw OBIS group semantics; no EcoFlow transport or endpoints.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

_OBIS = re.compile(r"^(\d+-\d+:\d+\.\d+\.\d+)((?:\([^()]*\))+)$")
_GROUP = re.compile(r"\(([^()]*)\)")
_MBUS = re.compile(r"^0-(\d+):24\.2\.[13]$")
_ELECTRICITY_KEYS = {"1-0:1.8.0", "1-0:1.8.1", "1-0:1.8.2", "1-0:2.8.0", "1-0:1.7.0", "1-0:2.7.0"}


class InvalidTelegram(ValueError):
    """HTTP response does not contain a valid DSMR-style telegram."""


@dataclass(frozen=True, slots=True)
class Telegram:
    raw: str
    obis: dict[str, tuple[str, ...]]

    def value(self, key: str) -> str | None:
        values = self.obis.get(key)
        return values[-1] if values else None

    def number(self, key: str, unit: str | None = None) -> Decimal | None:
        value = self.value(key)
        if value is None:
            return None
        number, sep, suffix = value.partition("*")
        if unit is not None and (not sep or suffix.lower() != unit.lower()):
            return None
        try:
            result = Decimal(number)
            return result if result.is_finite() else None
        except (InvalidOperation, ValueError):
            return None

    def mbus_readings(self) -> dict[int, tuple[Decimal, str]]:
        """Return available M-Bus channel values, retaining their actual units."""
        found = {}
        for key, groups in self.obis.items():
            match = _MBUS.fullmatch(key)
            if not match or len(groups) < 2:
                continue
            number, sep, unit = groups[-1].partition("*")
            if not sep or not unit:
                continue
            try:
                value = Decimal(number)
            except (InvalidOperation, ValueError):
                continue
            if value.is_finite():
                found[int(match[1])] = (value, unit)
        return found


def parse_telegram(raw: str) -> Telegram:
    """Extract DSMR/OBIS values without logging meter identifiers."""
    if not isinstance(raw, str) or len(raw) > 65536:
        raise InvalidTelegram("Invalid telegram text")
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    if not lines or not lines[0].startswith("/") or not any(line.startswith("!") for line in lines):
        raise InvalidTelegram("Missing DSMR framing")
    values = {}
    for line in lines[1:]:
        if line.startswith("!"):
            break
        match = _OBIS.fullmatch(line)
        if match:
            values[match[1]] = tuple(_GROUP.findall(match[2]))
    if not any(key in values for key in _ELECTRICITY_KEYS):
        raise InvalidTelegram("No electricity readings")
    return Telegram(raw=raw, obis=values)
