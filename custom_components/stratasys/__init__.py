"""The Stratasys Printer Integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .printer import StratasysMonitor, PrinterConfig

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Stratasys from a config entry."""

    # Get the user settings from the config flow
    config = entry.data

    # Create a PrinterConfig using the user-provided host and port
    printer_config = PrinterConfig(
        host=config["host"],
        port=config["port"],
        timeout=2.0,  # You can tweak other settings here if needed
        retry_attempts=3,
        log_level=20  # INFO level
    )

    # Create a monitor instance
    monitor = StratasysMonitor(printer_config)

    # Store the monitor instance in hass.data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = monitor

    # Try to connect immediately (optional, but good for early error detection)
    await monitor.connect()

    # Forward the setup to sensor platform (i.e., load sensor.py)
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "sensor")
    )

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    # Unload the sensor platform
    unload_ok = await hass.config_entries.async_forward_entry_unload(entry, "sensor")

    # Clean up: Close the printer connection
    monitor: StratasysMonitor = hass.data[DOMAIN].pop(entry.entry_id)
    monitor.cleanup()

    return unload_ok
