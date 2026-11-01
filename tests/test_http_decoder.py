"""Synthetic authenticated vectors and opt-in endpoint transport tests."""

from __future__ import annotations

import hashlib
import json
import unittest
from unittest.mock import AsyncMock

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .helpers import load_module
from .test_api import FakeResponse, FakeSession, api_module

decoder = load_module("custom_components.anker_solix_p1.http_decoder")
IP = "192.0.2.7"
SUFFIX = "0102030405"  # Synthetic test material only.


def encrypted(value, *, raw=None):
    """Build a vector independently from the integration decoder."""
    digest = hashlib.sha256(IP.encode() + bytes.fromhex(SUFFIX)).digest()
    plaintext = json.dumps(value).encode() if raw is None else raw
    return b"\x11\x00" + AESGCM(digest[:16]).encrypt(
        digest[16:28], plaintext, digest[8:24]
    )


class HttpDecoderTests(unittest.TestCase):
    def test_authenticates_json(self):
        self.assertEqual(
            decoder.HttpDecoder(IP, SUFFIX).decode(encrypted({"power": 123})),
            {"power": 123},
        )

    def test_rejects_wrong_ip_material_tampering_and_framing(self):
        body = encrypted({"secret": "synthetic"})
        for ip, suffix, content in (
            ("192.0.2.8", SUFFIX, body),
            (IP, "0504030201", body),
            (IP, SUFFIX, body[:-1] + bytes([body[-1] ^ 1])),
            (IP, SUFFIX, b"\x12\x00" + body[2:]),
            (IP, SUFFIX, body[:18]),
        ):
            with (
                self.subTest(ip=ip, suffix=suffix),
                self.assertRaises(decoder.HttpDecodeError),
            ):
                decoder.HttpDecoder(ip, suffix).decode(content)

    def test_rejects_invalid_authenticated_payload(self):
        for raw in (b"not JSON", b"\xff", b"[]", b"null"):
            with self.subTest(raw=raw), self.assertRaises(decoder.HttpDecodeError):
                decoder.HttpDecoder(IP, SUFFIX).decode(encrypted(None, raw=raw))

    def test_invalid_configuration_does_not_echo_inputs(self):
        for ip, suffix in (
            ("p1.local", SUFFIX),
            (IP, "private-invalid"),
            ("::1", SUFFIX),
        ):
            with self.assertRaises(decoder.HttpDecodeError) as raised:
                decoder.HttpDecoder(ip, suffix)
            self.assertNotIn(suffix, str(raised.exception))


class ExperimentalApiTests(unittest.IsolatedAsyncioTestCase):
    async def test_default_makes_no_experimental_requests(self):
        session = FakeSession(FakeResponse())
        api = api_module.AnkerP1Api(session, "p1.local")
        self.assertEqual(await api.async_get_experimental_data(), {})
        self.assertIsNone(session.url)

    async def test_all_routes_decode_and_fail_independently(self):
        api = api_module.AnkerP1Api(
            object(), IP, experimental_http=True, http_suffix=SUFFIX
        )
        responses = {
            "/api/measurement": encrypted({"power": 123}),
            "/api/wifi_info": b"broken",
            "/api/device_info": encrypted({"version": "synthetic"}),
        }
        api._client.async_get_encrypted_body = AsyncMock(
            side_effect=lambda path: responses[path]
        )
        result = await api.async_get_experimental_data()
        self.assertEqual(set(result), set(decoder.ENDPOINTS))
        self.assertEqual(result["/api/measurement"]["payload"], {"power": 123})
        self.assertEqual(result["/api/wifi_info"], {"status": "decode_failed"})
        self.assertEqual(result["/api/device_info"]["status"], "authenticated")

    async def test_request_failures_do_not_abort_other_routes(self):
        api = api_module.AnkerP1Api(
            object(), IP, experimental_http=True, http_suffix=SUFFIX
        )
        api._client.async_get_encrypted_body = AsyncMock(
            side_effect=api_module.AnkerP1TransportConnectionError("offline")
        )
        result = await api.async_get_experimental_data()
        self.assertTrue(
            all(item == {"status": "request_failed"} for item in result.values())
        )


class StreamingResponse(FakeResponse):
    def __init__(self, chunks, status=200):
        super().__init__()
        self.status = status
        self.chunks = chunks
        self.content = self

    async def iter_chunked(self, _size):
        for chunk in self.chunks:
            yield chunk


class ExperimentalTransportTests(unittest.IsolatedAsyncioTestCase):
    async def test_reads_binary_without_redirects(self):
        body = encrypted({"power": 123})
        session = FakeSession(StreamingResponse([body[:3], body[3:]]))
        api = api_module.AnkerP1Api(session, IP)
        result = await api._client.async_get_encrypted_body("/api/measurement")
        self.assertEqual(result, body)
        self.assertFalse(session.allow_redirects)
        self.assertEqual(session.url, f"http://{IP}/api/measurement")

    async def test_rejects_unlisted_paths_before_requesting(self):
        session = FakeSession(FakeResponse())
        api = api_module.AnkerP1Api(session, IP)
        with self.assertRaises(ValueError):
            await api._client.async_get_encrypted_body("/other")
        self.assertIsNone(session.url)

    async def test_bounds_response_size_and_rejects_redirect_status(self):
        for response in (
            StreamingResponse([b"x" * 4096] * 17),
            StreamingResponse([], status=302),
        ):
            api = api_module.AnkerP1Api(FakeSession(response), IP)
            with self.assertRaises(api_module.AnkerP1TransportResponseError):
                await api._client.async_get_encrypted_body("/api/measurement")
