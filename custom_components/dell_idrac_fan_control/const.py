"""Constants for Dell iDRAC Fan Control integration."""
from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "dell_idrac_fan_control"

CONF_BASE_PATH = "base_path"
CONF_ALLOW_INSECURE_TLS = "allow_insecure_tls"
CONF_IPMI_PORT = "ipmi_port"
CONF_IPMI_TIMEOUT = "ipmi_timeout"
CONF_POWER_OFF_MODE = "power_off_mode"

DEFAULT_PORT = 443
DEFAULT_USERNAME = "root"
DEFAULT_BASE_PATH = "/redfish/v1"
DEFAULT_TIMEOUT = 8
DEFAULT_ALLOW_INSECURE_TLS = True
DEFAULT_IPMI_PORT = 623
DEFAULT_IPMI_TIMEOUT = 5
DEFAULT_SCAN_INTERVAL = 30
DEFAULT_POWER_OFF_MODE = "graceful"

# Power-off behavior for the power switch's "off" action.
#   graceful -> ACPI soft shutdown (lets the OS shut down cleanly)
#   hard     -> immediate power down
POWER_OFF_MODES: list[str] = ["graceful", "hard"]

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.SELECT,
    Platform.SWITCH,
    Platform.BUTTON,
]
