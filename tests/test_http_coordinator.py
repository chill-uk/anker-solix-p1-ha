"""Verify optional HTTP results stay separate from sensor data and plain diagnostics."""

from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import AsyncMock

from .helpers import load_module
from .test_config_flow import _install_home_assistant_stubs
from .test_parser import TELEGRAM

_install_home_assistant_stubs()
sys.modules["homeassistant.config_entries"].ConfigEntry = object
sys.modules["homeassistant.core"].HomeAssistant = object
sys.modules["homeassistant.const"].__version__ = "test"
update = types.ModuleType("homeassistant.helpers.update_coordinator")


class CoordinatorStub:
    @classmethod
    def __class_getitem__(cls, _item):
        return cls


update.DataUpdateCoordinator = CoordinatorStub
update.UpdateFailed = RuntimeError
sys.modules[update.__name__] = update
constants = sys.modules["custom_components.anker_solix_p1.const"]
constants.TRANSIENT_FAILURE_GRACE_SECONDS = 15
coordinator_module = load_module("custom_components.anker_solix_p1.coordinator")
sys.modules["custom_components.anker_solix_p1"].AnkerP1ConfigEntry = object
loader = types.ModuleType("homeassistant.loader")
loader.async_get_integration = AsyncMock(
    return_value=types.SimpleNamespace(version="test")
)
sys.modules[loader.__name__] = loader
diagnostics_module = load_module("custom_components.anker_solix_p1.diagnostics")


class HttpCoordinatorTests(unittest.IsolatedAsyncioTestCase):
    async def test_optional_failure_preserves_dsmr_and_plain_diagnostics_are_safe(self):
        api = coordinator_module.AnkerP1Api.__new__(coordinator_module.AnkerP1Api)
        incoming = types.SimpleNamespace(raw_telegram=TELEGRAM, firmware_version="test")
        api.async_get_data = AsyncMock(return_value=incoming)
        api.async_get_experimental_data = AsyncMock(
            return_value={
                "/api/measurement": {"status": "decode_failed"},
                "/api/wifi_info": {
                    "status": "authenticated",
                    "payload": {"ssid": "PRIVATE-TEST-SSID"},
                },
            }
        )
        coordinator = coordinator_module.AnkerP1Coordinator.__new__(
            coordinator_module.AnkerP1Coordinator
        )
        coordinator.api = api
        coordinator.phase_mode = "single"
        coordinator.telegram_debug = False
        coordinator.encrypted_capture = coordinator_module.EncryptedDiagnosticCapture(
            True
        )
        coordinator._data_grace = types.SimpleNamespace(
            update=lambda value, *_args: value
        )
        data = await coordinator._async_update_data()
        self.assertIs(data, incoming)
        coordinator.data = data
        entry = types.SimpleNamespace(
            runtime_data=types.SimpleNamespace(coordinator=coordinator)
        )
        diagnostics = await diagnostics_module.async_get_config_entry_diagnostics(
            None, entry
        )
        self.assertEqual(
            diagnostics["experimental_http"]["/api/measurement"], "decode_failed"
        )
        self.assertEqual(
            diagnostics["experimental_http"]["/api/wifi_info"], "authenticated"
        )
        self.assertEqual(len(diagnostics["encrypted_records"]), 2)
        self.assertNotIn("PRIVATE-TEST-SSID", str(diagnostics))
        self.assertNotIn("payload", str(diagnostics))
