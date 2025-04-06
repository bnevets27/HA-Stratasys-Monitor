"""The Stratasys Printer integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN
from .printer import StratasysMonitor

async def async_setup(hass: HomeAssistant, config) -> bool:
    """Set up the Stratasys Printer integration."""
    # Nothing to do here for now, setup is fully handled by config entries
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Stratasys Printer from a config entry."""
    monitor = StratasysMonitor()

    try:
        # Attempt initial connection to printer
        await monitor.connect()
    except Exception as ex:
        # If connection fails, mark entry as not ready (HA will retry later)
        raise ConfigEntryNotReady(f"Printer not ready: {ex}") from ex

    # Store monitor object for use in coordinator and sensors
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = monitor

    # Now safely forward to the sensor platform
    await hass.config_entries.async_forward_entry_setup(entry, "sensor")

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Stratasys Printer config entry."""
    monitor: StratasysMonitor = hass.data[DOMAIN].pop(entry.entry_id, None)
    if monitor:
        monitor.cleanup()

    # Unload the sensor platform
    return await hass.config_entries.async_forward_entry_unload(entry, "sensor")
