"""Electricity, phase, M-Bus and connection diagnostics from DSMR."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import UnitOfEnergy, UnitOfPower, UnitOfElectricPotential, UnitOfElectricCurrent, UnitOfVolume, EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN


@dataclass(frozen=True)
class Description:
    key: str
    obis: str | None
    unit: str | None
    device_class: SensorDeviceClass | None
    state_class: SensorStateClass | None
    multiplier: int = 1
    diagnostic: bool = False


SENSORS = (
    Description("import_tariff_1", "1-0:1.8.1", "kWh", SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING),
    Description("import_tariff_2", "1-0:1.8.2", "kWh", SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING),
    Description("export_tariff_1", "1-0:2.8.1", "kWh", SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING),
    Description("export_tariff_2", "1-0:2.8.2", "kWh", SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING),
    Description("import_total", "1-0:1.8.0", "kWh", SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING),
    Description("export_total", "1-0:2.8.0", "kWh", SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING),
    Description("power_import", "1-0:1.7.0", "kW", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, 1000),
    Description("power_export", "1-0:2.7.0", "kW", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, 1000),
    Description("voltage_l1", "1-0:32.7.0", "V", SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT),
    Description("voltage_l2", "1-0:52.7.0", "V", SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT),
    Description("voltage_l3", "1-0:72.7.0", "V", SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT),
    Description("current_l1", "1-0:31.7.0", "A", SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT),
    Description("current_l2", "1-0:51.7.0", "A", SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT),
    Description("current_l3", "1-0:71.7.0", "A", SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT),
    Description("power_import_l1", "1-0:21.7.0", "kW", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, 1000),
    Description("power_export_l1", "1-0:22.7.0", "kW", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, 1000),
    Description("power_import_l2", "1-0:41.7.0", "kW", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, 1000),
    Description("power_export_l2", "1-0:42.7.0", "kW", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, 1000),
    Description("power_import_l3", "1-0:61.7.0", "kW", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, 1000),
    Description("power_export_l3", "1-0:62.7.0", "kW", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, 1000),
    Description("timeouts", None, None, None, SensorStateClass.TOTAL_INCREASING, diagnostic=True),
    Description("crc_errors", None, None, None, SensorStateClass.TOTAL_INCREASING, diagnostic=True),
    Description("telegrams", None, None, None, SensorStateClass.TOTAL_INCREASING, diagnostic=True),
)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = entry.runtime_data
    descriptions = [d for d in SENSORS if d.obis is None or d.obis in coordinator.data.telegram.obis]
    async_add_entities(AnkerP1Sensor(coordinator, entry, d) for d in descriptions)
    for channel, (value, unit) in coordinator.data.telegram.mbus_readings().items():
        if unit.lower() not in ("m3", "gj"):
            continue
        async_add_entities([AnkerP1MbusSensor(coordinator, entry, channel, unit)])


class AnkerP1Sensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry, description: Description):
        super().__init__(coordinator)
        self._desc = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_name = description.key.replace("_", " ").title()
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)}, name="Anker SOLIX P1", manufacturer="Anker", model="SOLIX P1")
        self._attr_entity_category = EntityCategory.DIAGNOSTIC if description.diagnostic else None
        self._attr_state_class = description.state_class
        self._attr_device_class = description.device_class
        units = {"kWh": UnitOfEnergy.KILO_WATT_HOUR, "kW": UnitOfPower.WATT, "V": UnitOfElectricPotential.VOLT,
                 "A": UnitOfElectricCurrent.AMPERE}
        self._attr_native_unit_of_measurement = units.get(description.unit)

    @property
    def native_value(self):
        d = self._desc
        if d.obis is not None:
            raw = self.coordinator.data.telegram.number(d.obis, d.unit)
            return float(raw * d.multiplier) if raw is not None else None
        return {"timeouts": self.coordinator.data.timeout_times, "crc_errors": self.coordinator.data.crc_error_times,
                "telegrams": self.coordinator.data.total_times}[d.key]


class AnkerP1MbusSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry, channel: int, unit: str):
        super().__init__(coordinator)
        self._channel = channel
        self._unit = unit
        self._attr_unique_id = f"{entry.entry_id}_mbus_{channel}_{unit}"
        self._attr_name = f"M-Bus {channel} {'Gas' if unit.lower() == 'm3' else 'Heat'}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)}, name="Anker SOLIX P1", manufacturer="Anker", model="SOLIX P1")
        self._attr_device_class = SensorDeviceClass.GAS if unit.lower() == "m3" else SensorDeviceClass.ENERGY
        self._attr_native_unit_of_measurement = UnitOfVolume.CUBIC_METERS if unit.lower() == "m3" else "GJ"
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING

    @property
    def native_value(self):
        reading = self.coordinator.data.telegram.mbus_readings().get(self._channel)
        return float(reading[0]) if reading is not None and reading[1].lower() == self._unit.lower() else None
