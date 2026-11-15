"""DataUpdateCoordinator for the Stratasys 3D Printer."""

import logging
from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry  # <--- ADD THIS
from .const import DOMAIN
from .printer import ConnectionError, StratasysMonitor

_LOGGER = logging.getLogger(__name__)

class PrinterDataCoordinator(DataUpdateCoordinator):
    """Coordinator to manage fetching data from the printer."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry, monitor: StratasysMonitor, scan_interval: int):
        """Initialize the coordinator."""
        super().__init__(
            hass,
            logger=_LOGGER,
            config_entry=config_entry,
            name="Stratasys Printer Data",
            update_interval=timedelta(seconds=scan_interval),
        )
        self._online_interval = timedelta(seconds=scan_interval)
        self.monitor = monitor
        self.config_entry = config_entry

    async def _async_update_data(self):
        """Fetch status, retaining an observable offline state and retrying slowly."""
        try:
            data = await self.monitor.get_status()
            if not isinstance(data, dict) or not any(
                isinstance(data.get(section), dict) and data[section]
                for section in ("general", "mariner", "currentJob")
            ):
                raise UpdateFailed("Printer returned empty or invalid status")
        except (ConnectionError, OSError) as ex:
            _LOGGER.debug("Printer status unavailable: %s", ex)
            self.update_interval = timedelta(minutes=5)
            return {"online": False}

        self.update_interval = self._online_interval
        return {**data, "online": True}
