"""The Stratasys Printer integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

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

    coordinator = PrinterDataCoordinator(hass, entry, monitor, entry.options.get("scan_interval", entry.data.get("scan_interval", 30)))
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Initial fetch
    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, ["sensor", "binary_sensor", "light", "switch"])

    entry.async_on_unload(entry.add_update_listener(async_update_options))

    return True

async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry so changed options take effect."""
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Stratasys Printer config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(
        entry, ["sensor", "binary_sensor", "light", "switch"]
    )
    if unloaded:
        coordinator: PrinterDataCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        coordinator.monitor.cleanup()
    return unloaded
