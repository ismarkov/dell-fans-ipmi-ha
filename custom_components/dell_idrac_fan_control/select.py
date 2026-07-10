"""Select platform — consolidated fan speed control (Auto + fixed %)."""
from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEFAULT_PORT, DOMAIN
from .coordinator import FanControlCoordinator

_LOGGER = logging.getLogger(__name__)

OPTION_AUTO = "Auto"
_STEP = 10
_PERCENT_OPTIONS = [f"{p}%" for p in range(_STEP, 101, _STEP)]  # 10% .. 100%
OPTIONS = [OPTION_AUTO, *_PERCENT_OPTIONS]

# After a fan command, the fans take a few seconds to spin up/down and the RPM
# readings come from the slower Redfish telemetry poll. Nudge that poll shortly
# after applying so the per-fan RPM sensors confirm the change within seconds
# rather than up to a full scan interval later.
_RPM_REFRESH_DELAYS = (5, 12)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the fan speed select entity."""
    coordinator: FanControlCoordinator = hass.data[DOMAIN][entry.entry_id]["fan_control"]
    async_add_entities([DellIdracFanSpeedSelect(coordinator, entry)])


class DellIdracFanSpeedSelect(
    CoordinatorEntity[FanControlCoordinator], SelectEntity
):
    """Single dropdown: Auto (Dell automatic curve) or a fixed fan speed."""

    _attr_has_entity_name = True
    _attr_translation_key = "fan_speed"
    _attr_icon = "mdi:fan"
    _attr_options = OPTIONS

    def __init__(
        self,
        coordinator: FanControlCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_fan_speed"

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
    def current_option(self) -> str | None:  # noqa: D102
        data = self.coordinator.data or {}
        mode = data.get("mode")
        if mode == "auto":
            return OPTION_AUTO
        if mode == "manual":
            speed = data.get("speed_percent")
            if speed is not None:
                opt = f"{int(speed)}%"
                return opt if opt in OPTIONS else None
        return None

    async def async_select_option(self, option: str) -> None:
        """Apply the selected fan setting, then refresh RPM telemetry."""
        if option == OPTION_AUTO:
            _LOGGER.info("Restoring Dell iDRAC automatic fan control")
            await self.coordinator.async_set_auto_mode()
        else:
            speed = int(option.rstrip("%"))
            _LOGGER.info("Setting Dell iDRAC fan speed to %d%%", speed)
            await self.coordinator.async_set_manual_speed(speed)
        self._schedule_rpm_refresh()

    def _schedule_rpm_refresh(self) -> None:
        """Kick the telemetry coordinator so RPM sensors reflect the change soon."""

        async def _refresh(_now) -> None:
            entry_data = self.hass.data.get(DOMAIN, {}).get(self._entry.entry_id)
            if not entry_data:  # entry unloaded before the delay elapsed
                return
            telemetry = entry_data.get("telemetry")
            if telemetry is not None:
                await telemetry.async_request_refresh()

        for delay in _RPM_REFRESH_DELAYS:
            async_call_later(self.hass, delay, _refresh)
