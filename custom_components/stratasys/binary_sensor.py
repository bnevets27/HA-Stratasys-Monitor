"""Binary sensor for Stratasys Printer."""

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN

MAX_FAILURES = 5  # Number of consecutive failures allowed

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up the binary sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([
        StratasysOnlineBinarySensor(coordinator, entry),
    ])

class StratasysOnlineBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of the printer's online status."""

    _attr_name = "Stratasys Printer Online"
    _attr_unique_id = "stratasys_printer_online"
    _attr_device_class = "connectivity"

    def __init__(self, coordinator, entry):
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.config_entry = entry
        self._failure_count = 0

    @property
    def is_on(self) -> bool:
        """Return True if the printer is considered online."""
        return self._failure_count < MAX_FAILURES

    def _handle_coordinator_update(self) -> None:
        """Handle a coordinator update."""
        if self.coordinator.last_update_success:
            self._failure_count = 0
        else:
            self._failure_count += 1

        self.async_write_ha_state()

    @property
    def device_info(self):
        """Return device info to group it properly under the printer device."""
        model = self.coordinator.data.get("general", {}).get("modelerType", "Unknown Model")
        return {
            "identifiers": {(DOMAIN, self.config_entry.entry_id)},
            "name": "Stratasys 3D Printer",
            "manufacturer": "Stratasys",
            "model": model,
        }
