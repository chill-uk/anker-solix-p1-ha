"""Raw local HTTP transport for the Anker SOLIX P1 Energy Tracker."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any

from aiohttp import ClientError, ClientSession

from .const import API_PATH, REQUEST_TIMEOUT


class AnkerP1TransportError(Exception):
    """Base exception for local transport failures."""


class AnkerP1TransportConnectionError(AnkerP1TransportError):
    """The Anker SOLIX P1 could not be reached."""


class AnkerP1TransportResponseError(AnkerP1TransportError):
    """The Anker SOLIX P1 returned an invalid HTTP/JSON response."""


class AnkerP1Client:
    """Fetch raw local data without interpreting DSMR content."""

    def __init__(self, session: ClientSession, host: str) -> None:
        self._session = session
        self._host = host

    @property
    def host(self) -> str:
        """Return the configured host."""
        return self._host

    async def async_get_encrypted_body(self, path: str) -> bytes:
        """Fetch an allowlisted experimental endpoint with bounded buffering."""
        from .http_decoder import ENDPOINTS

        if path not in ENDPOINTS:
            raise ValueError("Unsupported experimental endpoint")
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                async with self._session.get(
                    f"http://{self._host}{path}", allow_redirects=False
                ) as response:
                    response.raise_for_status()
                    if response.status != 200:
                        raise AnkerP1TransportResponseError("Unexpected HTTP status")
                    body = bytearray()
                    async for chunk in response.content.iter_chunked(4096):
                        body.extend(chunk)
                        if len(body) > 65536:
                            raise AnkerP1TransportResponseError(
                                "Encrypted response too large"
                            )
                    return bytes(body)
        except (TimeoutError, ClientError):
            raise AnkerP1TransportConnectionError(
                "Experimental HTTP request failed"
            ) from None

    async def async_get_debug_payload(self) -> Mapping[str, Any]:
        """Fetch one raw /getdebugdata payload."""
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                async with self._session.get(
                    f"http://{self._host}{API_PATH}", allow_redirects=False
                ) as response:
                    response.raise_for_status()
                    payload = await response.json(content_type=None)
        except TimeoutError as err:
            raise AnkerP1TransportConnectionError(
                f"Request to {API_PATH} timed out after {REQUEST_TIMEOUT} seconds"
            ) from err
        except ClientError as err:
            detail = str(err).strip() or type(err).__name__
            raise AnkerP1TransportConnectionError(
                f"Request to {API_PATH} failed: {detail}"
            ) from err
        except ValueError as err:
            raise AnkerP1TransportResponseError("Device returned invalid JSON") from err

        if not isinstance(payload, Mapping):
            raise AnkerP1TransportResponseError("JSON response is not an object")
        return payload
