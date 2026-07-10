"""Button platform — abrupt power actions via IPMI chassis control.

These are momentary, destructive actions (force off, power cycle, hard reset)
kept off the power switch on purpose. Add a Lovelace ``confirmation:`` tap
action on the dashboard if you want an "are you sure?" prompt — the backend
cannot enforce one.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.components.button import (
    ButtonDeviceClass,
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEFAULT_PORT, DOMAIN
from .coordinator import FanControlCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class DellIdracButtonDescription(ButtonEntityDescription):
    """Button description carrying the IPMI power action to send."""

    action: str = ""


BUTTONS: tuple[DellIdracButtonDescription, ...] = (
    DellIdracButtonDescription(
        key="force_off",
        translation_key="force_off",
        action="off",
        icon="mdi:power-plug-off",
    ),
    DellIdracButtonDescription(
        key="power_cycle",
        translation_key="power_cycle",
        action="cycle",
        device_class=ButtonDeviceClass.RESTART,
        icon="mdi:restart",
    ),
    DellIdracButtonDescription(
        key="hard_reset",
        translation_key="hard_reset",
        action="reset",
        device_class=ButtonDeviceClass.RESTART,
        icon="mdi:restart-alert",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the power action buttons."""
    coordinator: FanControlCoordinator = hass.data[DOMAIN][entry.entry_id]["fan_control"]
    async_add_entities(
        DellIdracPowerButton(coordinator, entry, desc) for desc in BUTTONS
    )


class DellIdracPowerButton(
    CoordinatorEntity[FanControlCoordinator], ButtonEntity
):
    """Momentary button issuing a single IPMI chassis power action."""

    _attr_has_entity_name = True
    entity_description: DellIdracButtonDescription

    def __init__(
        self,
        coordinator: FanControlCoordinator,
        entry: ConfigEntry,
        description: DellIdracButtonDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"

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

    async def async_press(self) -> None:
        """Send the chassis power action."""
        _LOGGER.info(
            "Dell server power action '%s' via IPMI", self.entity_description.key
        )
        await self.coordinator.async_set_power(self.entity_description.action)
