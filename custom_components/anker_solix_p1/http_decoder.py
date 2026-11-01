"""Experimental authenticated HTTP JSON decoding; no device secrets embedded."""

from __future__ import annotations

import hashlib
import ipaddress
import json
import re
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ENDPOINTS = ("/api/measurement", "/api/wifi_info", "/api/device_info")


class HttpDecodeError(ValueError):
    """A response could not be authenticated or interpreted safely."""


def validate_material(host: str, suffix_hex: str) -> bytes:
    """Require a literal IPv4 address and exactly five hex-encoded bytes."""
    try:
        ipaddress.IPv4Address(host)
    except ipaddress.AddressValueError:
        raise HttpDecodeError(
            "Experimental decoding requires a literal IPv4 address"
        ) from None
    if not isinstance(suffix_hex, str) or not re.fullmatch(
        r"[0-9a-fA-F]{10}", suffix_hex
    ):
        raise HttpDecodeError(
            "Experimental derivation value must contain ten hex digits"
        )
    return bytes.fromhex(suffix_hex)


class HttpDecoder:
    """Authenticate before parsing, using the device's current IPv4 address."""

    def __init__(self, host: str, suffix_hex: str) -> None:
        suffix = validate_material(host, suffix_hex)
        digest = hashlib.sha256(host.encode("ascii") + suffix).digest()
        self._cipher = AESGCM(digest[:16])
        self._nonce = digest[16:28]
        self._aad = digest[8:24]

    def decode(self, body: bytes) -> dict[str, Any]:
        """Decode the version prefix and ciphertext followed by a 16-byte tag."""
        if len(body) <= 18 or body[:2] != b"\x11\x00":
            raise HttpDecodeError("Unsupported encrypted response framing")
        try:
            plaintext = self._cipher.decrypt(self._nonce, body[2:], self._aad)
        except InvalidTag:
            raise HttpDecodeError("Encrypted response authentication failed") from None
        try:
            payload = json.loads(plaintext.decode("utf-8"))
        except (ValueError, UnicodeError, RecursionError):
            raise HttpDecodeError("Authenticated response is not valid JSON") from None
        if not isinstance(payload, dict):
            raise HttpDecodeError("Authenticated response is not a JSON object")
        return payload
