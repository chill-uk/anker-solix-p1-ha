"""Offline tests for Anker JSON's DSMR telegram parser."""
from __future__ import annotations

import importlib.util
import pathlib
import sys

import pytest

path = pathlib.Path(__file__).resolve().parents[1] / "custom_components" / "anker_solix_p1" / "parser.py"
spec = importlib.util.spec_from_file_location("anker_parser", path)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

TELEGRAM = (
    "/ISK5\\2M550E-1011\r\n\r\n"
    "1-3:0.2.8(50)\r\n"
    "1-0:1.8.1(014751.188*kWh)\r\n"
    "1-0:1.7.0(00.309*kW)\r\n"
    "1-0:32.7.0(237.8*V)\r\n"
    "0-1:24.1.0(003)\r\n"
    "0-1:24.2.1(261029070506W)(11155.480*m3)\r\n"
    "!8481\r\n"
)


def test_realistic_anker_telegram():
    t = module.parse_telegram(TELEGRAM)
    assert str(t.number("1-0:1.8.1", "kWh")) == "14751.188"
    assert str(t.number("1-0:1.7.0", "kW") * 1000) == "309.000"
    assert str(t.number("1-0:32.7.0", "V")) == "237.8"
    assert t.mbus_readings()[1][1] == "m3"
    assert str(t.mbus_readings()[1][0]) == "11155.480"


def test_rejects_invalid():
    with pytest.raises(module.InvalidTelegram):
        module.parse_telegram("not a telegram")


def test_rejects_unrealistic_payload():
    with pytest.raises(module.InvalidTelegram):
        module.parse_telegram("/ISK\r\n1-0:1.7.0(1*kW)\r\n")
