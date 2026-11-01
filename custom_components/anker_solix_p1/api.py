"""Local API facade for the Anker SOLIX P1 Energy Tracker."""

from __future__ import annotations

import asyncio
from typing import Any

from aiohttp import ClientSession

from .client import (
    AnkerP1Client,
    AnkerP1TransportConnectionError,
    AnkerP1TransportResponseError,
)
from .http_decoder import ENDPOINTS, HttpDecodeError, HttpDecoder
from .models import AnkerP1Data
from .parser import InvalidTelegramError, parse_telegram
from .validation import CrcResult, validate_crc


class AnkerP1Error(Exception):
    """Base exception for Anker SOLIX P1 communication errors."""


class AnkerP1ConnectionError(AnkerP1Error):
    """The Anker SOLIX P1 could not be reached."""


class AnkerP1ResponseError(AnkerP1Error):
    """The Anker SOLIX P1 returned an invalid response."""


class AnkerP1TelegramError(AnkerP1ResponseError):
    """The Anker SOLIX P1 returned a telegram that failed integrity or parsing."""

    def __init__(self, message: str, telegram: str, crc: CrcResult) -> None:
        """Initialize an error containing data needed for safe debug logging."""
        super().__init__(message)
        self.telegram = telegram
        self.crc = crc


class AnkerP1Api:
    """Async facade combining raw HTTP transport and DSMR interpretation."""

    def __init__(
        self,
        session: ClientSession,
        host: str,
        *,
        experimental_http: bool = False,
        http_suffix: str = "",
    ) -> None:
        """Initialize the API facade."""
        self._client = AnkerP1Client(session, host)
        self._http_decoder = (
            HttpDecoder(host, http_suffix) if experimental_http else None
        )

    async def async_get_experimental_data(self) -> dict[str, Any]:
        """Read optional endpoints independently; never return unauthenticated bytes."""
        if self._http_decoder is None:
            return {}

        async def fetch(path: str) -> tuple[str, dict[str, Any]]:
            try:
                body = await self._client.async_get_encrypted_body(path)
                payload = self._http_decoder.decode(body)
            except HttpDecodeError:
                return path, {"status": "decode_failed"}
            except (AnkerP1TransportConnectionError, AnkerP1TransportResponseError):
                return path, {"status": "request_failed"}
            return path, {"status": "authenticated", "payload": payload}

        return dict(await asyncio.gather(*(fetch(path) for path in ENDPOINTS)))

    @property
    def host(self) -> str:
        """Return the configured host."""
        return self._client.host

    async def async_get_data(self) -> AnkerP1Data:
        """Fetch and parse one response from /getdebugdata."""
        try:
            payload = await self._client.async_get_debug_payload()
        except AnkerP1TransportConnectionError as err:
            raise AnkerP1ConnectionError(str(err)) from err
        except AnkerP1TransportResponseError as err:
            raise AnkerP1ResponseError(str(err)) from err

        telegram_raw = payload.get("debugdata")
        if not isinstance(telegram_raw, str):
            raise AnkerP1ResponseError("JSON response has no debugdata telegram")

        crc = validate_crc(telegram_raw)
        if not crc.valid:
            raise AnkerP1TelegramError(
                crc.error or "Telegram CRC validation failed", telegram_raw, crc
            )

        try:
            telegram = parse_telegram(telegram_raw)
        except InvalidTelegramError as err:
            raise AnkerP1TelegramError(str(err), telegram_raw, crc) from err

        return AnkerP1Data(
            telegram=telegram,
            serial=_optional_string(payload.get("SN")),
            firmware_version=_optional_string(payload.get("VERSION_ALL")),
            timeout_times=_optional_int(payload.get("timeout_times")),
            crc_error_times=_optional_int(payload.get("crc_error_times")),
            total_times=_optional_int(payload.get("total_times")),
            raw_telegram=telegram_raw,
        )


def _optional_string(value: Any) -> str | None:
    """Return a trimmed non-empty string."""
    return value.strip() if isinstance(value, str) and value.strip() else None


def _optional_int(value: Any) -> int | None:
    """Return an integer without allowing malformed metadata to fail an update."""
    if isinstance(value, bool):
        return None
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


# Re-export transport errors to preserve the integration's existing import surface.
__all__ = [
    "AnkerP1Api",
    "AnkerP1ConnectionError",
    "AnkerP1Error",
    "AnkerP1ResponseError",
    "AnkerP1TelegramError",
]
