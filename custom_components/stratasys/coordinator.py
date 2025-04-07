"""DataUpdateCoordinator for the Stratasys 3D Printer."""

import logging
from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry  # <--- ADD THIS
from .const import DOMAIN
from .printer import StratasysMonitor

_LOGGER = logging.getLogger(__name__)

class PrinterDataCoordinator(DataUpdateCoordinator):
    """Coordinator to manage fetching data from the printer."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry, monitor: StratasysMonitor, scan_interval: int):
        """Initialize the coordinator."""
        super().__init__(
            hass,
            logger=_LOGGER,
            name="Stratasys Printer Data",
            update_interval=timedelta(seconds=scan_interval),
        )
        self.monitor = monitor
        self.config_entry = config_entry  # <--- STORE the entry for device_info later!

    async def _async_update_data(self):
        """Fetch latest data from the printer."""
        try:
            return await self.monitor.get_status()
        except Exception as ex:
            raise Exception(f"Error updating printer data: {ex}")
