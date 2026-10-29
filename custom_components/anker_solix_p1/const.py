"""Constants for the local-only Anker SOLIX P1 integration."""
from homeassistant.const import Platform

DOMAIN = "anker_solix_p1"
PLATFORMS = (Platform.SENSOR,)
DEFAULT_SCAN_INTERVAL = 10
CONF_SCAN_INTERVAL = "scan_interval"
MIN_SCAN_INTERVAL = 5
MAX_SCAN_INTERVAL = 300
PATH = "/getdebugdata"
