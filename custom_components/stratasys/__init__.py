"""The Stratasys Printer integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN
from .printer import PrinterConfig, StratasysMonitor
from .coordinator import PrinterDataCoordinator

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Stratasys Printer integration from YAML (not used)."""
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Stratasys Printer from a config entry."""
    config = PrinterConfig(
        host=entry.data["host"],
        port=entry.data["port"],
        timeout=2.0,
        retry_attempts=3,
        retry_delay=1.0,
        packet_size=64,
    )

    monitor = StratasysMonitor(config)

    try:
        # Only test the connection, don't fetch status here
        await monitor.connect()
    except Exception as ex:
        raise ConfigEntryNotReady(f"Printer not ready: {ex}") from ex

    coordinator = PrinterDataCoordinator(hass, entry, monitor, entry.options.get("scan_interval", 30))
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Initial fetch
    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, ["sensor", "binary_sensor"])

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Stratasys Printer config entry."""
    coordinator: PrinterDataCoordinator = hass.data[DOMAIN].pop(entry.entry_id)

    # ✅ Properly cleanup socket
    coordinator.monitor.cleanup()

    return await hass.config_entries.async_forward_entry_unload(entry, ["sensor", "binary_sensor"])
