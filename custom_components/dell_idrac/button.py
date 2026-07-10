"""Button platform — server power actions via IPMI chassis control.

Power is exposed as explicit, momentary actions rather than a toggle: a server
isn't a light switch, and a deliberate "Power On" / "Graceful Shutdown" pair is
clearer and safer than a switch that can be flipped by accident. The read-only
Power State sensor is the on/off indicator. Add a Lovelace ``confirmation:`` tap
action on the destructive buttons if you want an "are you sure?" prompt — the
backend cannot enforce one.
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
    """Button description carrying the IPMI power action and its precondition."""

    action: str = ""
    # Power state in which this action is meaningful: "off" = only when the
    # server is off (Power On), "on" = only when it is on (shutdown/reset),
    # None = always. Used to grey out actions that can't apply.
    requires_power: str | None = None


BUTTONS: tuple[DellIdracButtonDescription, ...] = (
    DellIdracButtonDescription(
        key="power_on",
        translation_key="power_on",
        action="on",
        requires_power="off",
        icon="mdi:power",
    ),
    DellIdracButtonDescription(
        key="graceful_shutdown",
        translation_key="graceful_shutdown",
        action="soft_off",
        requires_power="on",
        icon="mdi:power-standby",
    ),
    DellIdracButtonDescription(
        key="force_off",
        translation_key="force_off",
        action="off",
        requires_power="on",
        icon="mdi:power-plug-off",
    ),
    DellIdracButtonDescription(
        key="power_cycle",
        translation_key="power_cycle",
        action="cycle",
        requires_power="on",
        device_class=ButtonDeviceClass.RESTART,
        icon="mdi:restart",
    ),
    DellIdracButtonDescription(
        key="hard_reset",
        translation_key="hard_reset",
        action="reset",
        requires_power="on",
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
        if not (super().available and data.get("connection_ok")):
            return False
        # Grey out actions that can't apply in the current power state. When the
        # state is unknown (None), leave the button available so the user can
        # still act.
        power_on = data.get("power_on")
        req = self.entity_description.requires_power
        if req == "on" and power_on is False:
            return False
        if req == "off" and power_on is True:
            return False
        return True

    async def async_press(self) -> None:
        """Send the chassis power action."""
        _LOGGER.info(
            "Dell server power action '%s' via IPMI", self.entity_description.key
        )
        await self.coordinator.async_set_power(self.entity_description.action)
