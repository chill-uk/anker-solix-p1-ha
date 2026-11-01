"""Verify standalone HTTP readouts use the existing support encryption."""

import base64
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from nacl.public import PrivateKey

from .helpers import INTEGRATION
from .test_decrypt_diagnostics import capture_module, decrypt_module


class HttpReadoutEncryptionTests(unittest.TestCase):
    def test_support_decryptor_round_trip_keeps_ip_and_bytes_private(self):
        key = PrivateKey.generate()
        body = b"\x11\x00" + b"SYNTHETIC-PRIVATE-RESPONSE"
        envelope = capture_module.encrypt_http_readout(
            "192.0.2.7",
            {"measurement.bin": body},
            firmware_version="test",
            public_key=base64.b64encode(bytes(key.public_key)).decode(),
        )
        exported = json.dumps(envelope)
        self.assertNotIn("192.0.2.7", exported)
        self.assertNotIn(base64.b64encode(body).decode(), exported)
        self.assertNotIn("SYNTHETIC-PRIVATE-RESPONSE", exported)
        result = decrypt_module.decrypt_diagnostics(
            envelope, base64.b64encode(bytes(key)).decode()
        )
        record = result["decrypted_records"][0]
        self.assertEqual(record["device_ip"], "192.0.2.7")
        self.assertEqual(record["firmware_version"], "test")
        encoded = record["responses"]["/api/measurement"]["body_base64"]
        self.assertEqual(base64.b64decode(encoded), body)
        with self.assertRaises(ValueError):
            decrypt_module.decrypt_diagnostics(
                envelope, base64.b64encode(bytes(PrivateKey.generate())).decode()
            )

    def test_rejects_bad_ip_wrong_filenames_and_malformed_or_large_inputs(self):
        body = b"\x11\x00" + b"x" * 20
        for ip, files in (
            ("p1.local", {"measurement.bin": body}),
            ("192.0.2.7", {}),
            ("192.0.2.7", {"unknown.bin": body}),
            ("192.0.2.7", {"measurement.bin": b"error page"}),
            ("192.0.2.7", {"measurement.bin": b"\x11\x00" + b"x" * 65536}),
        ):
            with self.subTest(ip=ip), self.assertRaises(ValueError):
                capture_module.encrypt_http_readout(ip, files)

    def test_cli_runs_without_home_assistant_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            source = folder / "measurement.bin"
            source.write_bytes(b"\x11\x00" + b"x" * 20)
            output = folder / "sealed.json"
            command = [
                sys.executable,
                str(INTEGRATION / "capture.py"),
                "--ip",
                "192.0.2.7",
                "--output",
                str(output),
                str(source),
            ]
            first = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            original = output.read_bytes()
            second = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(second.returncode, 1)
            self.assertEqual(output.read_bytes(), original)
            self.assertNotIn("192.0.2.7", first.stdout + second.stdout)

    def test_cli_bad_input_does_not_write_output(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "sealed.json"
            with patch.object(
                sys,
                "argv",
                [
                    "capture.py",
                    "--ip",
                    "invalid",
                    "--output",
                    str(output),
                    "missing.bin",
                ],
            ):
                self.assertEqual(capture_module.main(), 1)
            self.assertFalse(output.exists())
