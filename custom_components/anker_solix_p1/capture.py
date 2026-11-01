"""Encrypted, bounded DSMR capture for support diagnostics."""

from __future__ import annotations

import base64
import json
import time
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any, Final

from nacl.public import PublicKey, SealedBox

CAPTURE_DURATION_SECONDS: Final = 10 * 60
CAPTURE_MAX_RECORDS: Final = 120
SUPPORT_KEY_ID: Final = "support-2026-01"
SUPPORT_PUBLIC_KEY: Final = "YcKfN202beTpo3uLz7mXrnKUqH93dLQTS4YL/QmQZy8="


class EncryptedDiagnosticCapture:
    """Encrypt diagnostic records immediately and retain ciphertext only."""

    def __init__(
        self,
        enabled: bool,
        *,
        public_key: str = SUPPORT_PUBLIC_KEY,
        key_id: str = SUPPORT_KEY_ID,
        now: Callable[[], datetime] | None = None,
        monotonic: Callable[[], float] | None = None,
    ) -> None:
        """Initialize a bounded capture session."""
        self.enabled = enabled
        self.key_id = key_id
        self._now = now or (lambda: datetime.now(UTC))
        self._monotonic = monotonic or time.monotonic
        self._box = (
            SealedBox(PublicKey(base64.b64decode(public_key, validate=True)))
            if enabled
            else None
        )
        self._started_at = self._now() if enabled else None
        self._started_monotonic = self._monotonic() if enabled else None
        self._stopped_at: datetime | None = None
        self._stop_reason: str | None = None
        self._encrypted_records: list[str] = []

    @property
    def active(self) -> bool:
        """Return whether capture can accept another record."""
        if not self.enabled or self._stop_reason is not None:
            return False
        if len(self._encrypted_records) >= CAPTURE_MAX_RECORDS:
            self._stop("record_limit")
            return False
        if (
            self._started_monotonic is not None
            and self._monotonic() - self._started_monotonic >= CAPTURE_DURATION_SECONDS
        ):
            self._stop("duration_limit")
            return False
        return True

    def capture(self, record: Mapping[str, Any]) -> None:
        """Encrypt and retain one JSON record without retaining its plaintext."""
        if not self.active or self._box is None:
            return

        payload = {
            "captured_at": self._now().isoformat(),
            **record,
        }
        plaintext = json.dumps(
            payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True
        ).encode()
        ciphertext = self._box.encrypt(plaintext)
        self._encrypted_records.append(base64.b64encode(ciphertext).decode("ascii"))

        if len(self._encrypted_records) >= CAPTURE_MAX_RECORDS:
            self._stop("record_limit")

    def diagnostics(self) -> dict[str, Any]:
        """Return safe capture metadata and encrypted records."""
        active = self.active
        if not self.enabled:
            status = "disabled"
        elif active:
            status = "active"
        else:
            status = "complete"

        return {
            "enabled": self.enabled,
            "status": status,
            "key_id": self.key_id,
            "algorithm": "libsodium_sealed_box_curve25519xsalsa20poly1305",
            "started_at": (
                self._started_at.isoformat() if self._started_at is not None else None
            ),
            "stopped_at": (
                self._stopped_at.isoformat() if self._stopped_at is not None else None
            ),
            "stop_reason": self._stop_reason,
            "duration_limit_seconds": CAPTURE_DURATION_SECONDS,
            "record_limit": CAPTURE_MAX_RECORDS,
            "records_captured": len(self._encrypted_records),
            "encrypted_records": list(self._encrypted_records),
        }

    def clear(self) -> None:
        """Discard all encrypted records."""
        self._encrypted_records.clear()
        self.enabled = False
        self._box = None
        self._stop_reason = "cleared"
        self._stopped_at = self._now()

    def _stop(self, reason: str) -> None:
        """Mark the capture complete."""
        if self._stop_reason is None:
            self._stop_reason = reason
            self._stopped_at = self._now()


def encrypt_http_readout(
    device_ip: str,
    files: Mapping[str, bytes],
    *,
    firmware_version: str | None = None,
    public_key: str = SUPPORT_PUBLIC_KEY,
    key_id: str = SUPPORT_KEY_ID,
) -> dict[str, Any]:
    """Seal endpoint bodies and derivation IP in a support-compatible envelope."""
    from ipaddress import IPv4Address

    device_ip = str(IPv4Address(device_ip))
    endpoints = {
        "measurement.bin": "/api/measurement",
        "wifi_info.bin": "/api/wifi_info",
        "device_info.bin": "/api/device_info",
    }
    if not files or not files.keys() <= endpoints.keys():
        raise ValueError("Choose measurement.bin, wifi_info.bin, or device_info.bin")
    for body in files.values():
        if not 18 < len(body) <= 65536 or body[:2] != b"\x11\x00":
            raise ValueError("Input is not a supported binary endpoint response")
    capture = EncryptedDiagnosticCapture(True, public_key=public_key, key_id=key_id)
    capture.capture(
        {
            "outcome": "http_readout",
            "device_ip": device_ip,
            "firmware_version": firmware_version,
            "responses": {
                endpoints[name]: {"body_base64": base64.b64encode(body).decode("ascii")}
                for name, body in files.items()
            },
        }
    )
    return {"schema_version": 1, **capture.diagnostics()}


def main() -> int:
    """Encrypt curl readouts locally without importing Home Assistant."""
    import argparse
    import os
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Encrypt P1 readouts for support.")
    parser.add_argument("--ip", required=True, help="P1 IPv4 address at capture time")
    parser.add_argument("--firmware", help="Optional firmware version")
    parser.add_argument(
        "--output", type=Path, default=Path("http-readout.encrypted.json")
    )
    parser.add_argument("files", type=Path, nargs="+", help="Original curl .bin files")
    args = parser.parse_args()
    try:
        if not 1 <= len(args.files) <= 3:
            raise ValueError("Choose one to three endpoint files")
        files = {}
        for path in args.files:
            if path.name in files:
                raise ValueError("Duplicate endpoint file")
            with path.open("rb") as stream:
                files[path.name] = stream.read(65537)
        envelope = encrypt_http_readout(args.ip, files, firmware_version=args.firmware)
        content = (json.dumps(envelope, indent=2) + "\n").encode()
        fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
    except (OSError, ValueError):
        print("Encryption failed: check IP, input files, and a new output filename.")
        return 1
    print("Encrypted readout saved. Send only the .encrypted.json file to support.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
