"""Read only Anker's confirmed GET /getdebugdata endpoint."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aiohttp import ClientError, ClientSession, ClientTimeout

from .const import PATH
from .parser import InvalidTelegram, Telegram, parse_telegram


class AnkerP1Error(Exception):
    """Communication or response failure."""


@dataclass(frozen=True, slots=True)
class AnkerP1Data:
    telegram: Telegram
    timeout_times: int | None
    crc_error_times: int | None
    total_times: int | None


def _counter(payload: dict[str, Any], name: str) -> int | None:
    value = payload.get(name)
    if type(value) is int and value >= 0:
        return value
    return None


class AnkerP1Api:
    """Only talks to the Anker local debugdata endpoint."""

    def __init__(self, session: ClientSession, host: str) -> None:
        self._session = session
        self._url = f"http://{host}{PATH}"

    async def async_get_data(self) -> AnkerP1Data:
        try:
            async with self._session.get(self._url, timeout=ClientTimeout(total=8)) as response:
                response.raise_for_status()
                # The response is JSON with 'debugdata', not raw DSMR or an encrypted API.
                if response.content_length is not None and response.content_length > 65536:
                    raise AnkerP1Error("Oversized response")
                payload = await response.json(content_type=None)
        except (ClientError, TimeoutError, ValueError) as err:
            raise AnkerP1Error("Unable to retrieve Anker P1 debug data") from err
        if not isinstance(payload, dict):
            raise AnkerP1Error("Unexpected response structure")
        try:
            telegram = parse_telegram(payload.get("debugdata"))
        except InvalidTelegram as err:
            raise AnkerP1Error("Response did not contain a usable DSMR telegram") from err
        return AnkerP1Data(
            telegram=telegram,
            timeout_times=_counter(payload, "timeout_times"),
            crc_error_times=_counter(payload, "crc_error_times"),
            total_times=_counter(payload, "total_times"),
        )
