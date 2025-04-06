"""DataUpdateCoordinator for the Stratasys 3D Printer."""

from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.core import HomeAssistant
from .const import DOMAIN
from .printer import StratasysMonitor

class PrinterDataCoordinator(DataUpdateCoordinator):
    """Coordinator to manage fetching data from the printer."""

    def __init__(self, hass: HomeAssistant, monitor: StratasysMonitor, scan_interval: int):
        """Initialize the coordinator."""
        super().__init__(
            hass,
            logger=hass.logger,
            name="Stratasys Printer Data",
            update_interval=timedelta(seconds=scan_interval),
        )
        self.monitor = monitor

    async def _async_update_data(self):
        """Fetch data from the printer."""
        try:
            return await self.monitor.get_status()
        except Exception as ex:
            raise Exception(f"Error updating printer data: {ex}")
