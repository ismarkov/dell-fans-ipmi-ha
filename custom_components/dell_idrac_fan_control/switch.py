"""Switch platform — server power on/off via IPMI chassis control."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_POWER_OFF_MODE,
    DEFAULT_PORT,
    DEFAULT_POWER_OFF_MODE,
    DOMAIN,
)
from .coordinator import FanControlCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the server power switch."""
    coordinator: FanControlCoordinator = hass.data[DOMAIN][entry.entry_id]["fan_control"]
    async_add_entities([DellIdracPowerSwitch(coordinator, entry)])


class DellIdracPowerSwitch(
    CoordinatorEntity[FanControlCoordinator], SwitchEntity
):
    """Switch representing host power state (on / off) over IPMI.

    Turning off performs a graceful ACPI shutdown by default; set the
    integration's "power off mode" option to "hard" for an immediate power
    down. Abrupt actions (force off, cycle, reset) are exposed as buttons.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "power"
    _attr_device_class = SwitchDeviceClass.OUTLET
    _attr_icon = "mdi:server"

    def __init__(
        self,
        coordinator: FanControlCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_power"

    @property
    def device_info(self) -> DeviceInfo:  # noqa: D102
        cfg = self._entry.data
        telemetry = self.hass.data[DOMAIN][self._entry.entry_id].get("telemetry")
        data = telemetry.data if telemetry else None
        sys = (data.get("system") or {}) if data else {}
        mgr = (data.get("manager") or {}) if data else {}
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=f"Dell iDRAC ({cfg[CONF_HOST]})",
            manufacturer="Dell",
            model=sys.get("model"),
            sw_version=mgr.get("firmware_version"),
            serial_number=sys.get("service_tag") or sys.get("serial_number"),
            configuration_url=f"https://{cfg[CONF_HOST]}:{cfg.get(CONF_PORT, DEFAULT_PORT)}",
        )

    @property
    def available(self) -> bool:  # noqa: D102
        data = self.coordinator.data or {}
        return super().available and bool(data.get("connection_ok"))

    @property
    def is_on(self) -> bool | None:  # noqa: D102
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("power_on")

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Power the server on."""
        if self.is_on:
            return
        _LOGGER.info("Powering on Dell server via IPMI")
        await self.coordinator.async_set_power("on")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Power the server off (graceful ACPI shutdown, or hard if configured)."""
        if self.is_on is False:
            return
        cfg = {**self._entry.data, **self._entry.options}
        mode = cfg.get(CONF_POWER_OFF_MODE, DEFAULT_POWER_OFF_MODE)
        action = "off" if mode == "hard" else "soft_off"
        _LOGGER.info("Powering off Dell server via IPMI (%s)", mode)
        await self.coordinator.async_set_power(action)
