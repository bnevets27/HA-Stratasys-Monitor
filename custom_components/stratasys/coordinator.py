"""DataUpdateCoordinator for the Stratasys 3D Printer."""

from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .printer import StratasysMonitor

SCAN_INTERVAL = timedelta(seconds=30)

class PrinterDataCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch data from the Stratasys 3D printer."""

    def __init__(self, hass: HomeAssistant, monitor: StratasysMonitor):
        """Initialize the coordinator."""
        super().__init__(
            hass,
            logger=hass.logger,
            name="Stratasys Printer Data",
            update_interval=SCAN_INTERVAL,
        )
        self.monitor = monitor

    async def _async_update_data(self):
        """Fetch latest data from the printer."""
        try:
            return await self.monitor.get_status()
        except Exception as ex:
            raise Exception(f"Error updating printer data: {ex}")
