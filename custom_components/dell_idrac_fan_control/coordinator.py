"""Data update coordinators for Dell iDRAC Fan Control."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .ipmi import IpmiClient, IpmiError
from .redfish import RedfishClient, RedfishError

_LOGGER = logging.getLogger(__name__)


class TelemetryCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetches Redfish system / manager / thermal / power data."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: RedfishClient,
        scan_interval: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="Dell iDRAC Telemetry",
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.client.get_all_data()
        except RedfishError as exc:
            raise UpdateFailed(str(exc)) from exc


class FanControlCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Probes IPMI connectivity and tracks fan-control state."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: IpmiClient,
        scan_interval: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="Dell iDRAC Fan Control",
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client
        self._mode: str = "unknown"
        self._speed: int | None = None
        # Optimistic power state held until a real reading confirms it, so the
        # switch reflects the command immediately during the seconds-long
        # power transition rather than showing the pre-command state.
        self._power_optimistic: bool | None = None

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            status = await self.client.get_status()
        except IpmiError as exc:
            _LOGGER.debug("IPMI probe failed: %s", exc)
            return {
                "connection_ok": False,
                "device_info": None,
                "power_on": None,
                "mode": self._mode,
                "speed_percent": self._speed,
                "error": str(exc),
            }

        real = status.get("power_on")
        if self._power_optimistic is not None and real == self._power_optimistic:
            self._power_optimistic = None
        power_on = (
            self._power_optimistic if self._power_optimistic is not None else real
        )
        return {
            "connection_ok": True,
            "device_info": status.get("device_info"),
            "power_on": power_on,
            "mode": self._mode,
            "speed_percent": self._speed,
            "error": None,
        }

    async def async_set_auto_mode(self) -> None:
        """Send Dell auto-fan command via IPMI."""
        await self.client.set_automatic_fan_mode()
        self._mode = "auto"
        self._speed = None
        await self.async_request_refresh()

    async def async_set_manual_speed(self, speed: int) -> None:
        """Send Dell manual-fan-speed command via IPMI."""
        await self.client.set_manual_fan_speed(speed)
        self._mode = "manual"
        self._speed = speed
        await self.async_request_refresh()

    async def async_set_power(self, action: str) -> None:
        """Send a chassis power command via IPMI (on/off/soft_off/cycle/reset)."""
        await self.client.set_power(action)
        if action == "on":
            self._power_optimistic = True
        elif action in ("off", "soft_off"):
            self._power_optimistic = False
        else:
            # cycle / reset: transient off→on; let the real reading settle it.
            self._power_optimistic = None
        await self.async_request_refresh()
