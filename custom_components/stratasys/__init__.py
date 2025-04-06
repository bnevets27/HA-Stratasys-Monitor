"""The Stratasys Printer integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from .const import DOMAIN
from .printer import StratasysMonitor

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Stratasys Printer component."""
    # Nothing to do here for now, we rely fully on config entries
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Stratasys Printer from a config entry."""
    monitor = StratasysMonitor()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = monitor

    # 🚨 FIX: Make sure to await forwarding setup
    await hass.config_entries.async_forward_entry_setup(entry, "sensor")

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Stratasys Printer config entry."""
    monitor: StratasysMonitor = hass.data[DOMAIN].pop(entry.entry_id, None)
    if monitor:
        monitor.cleanup()

    # 🚨 FIX: Make sure to await unloading
    return await hass.config_entries.async_forward_entry_unload(entry, "sensor")
