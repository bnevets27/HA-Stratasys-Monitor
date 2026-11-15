"""Binary sensor for Stratasys Printer."""

import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
_LEGACY_UNIQUE_ID = "stratasys_printer_online"

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up the binary sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    sensor = StratasysOnlineBinarySensor(coordinator, entry)

    # Update the existing record before adding the entity so its entity ID and
    # user customizations survive. Another printer must not claim this record.
    registry = er.async_get(hass)
    legacy_entity_id = registry.async_get_entity_id(
        "binary_sensor", DOMAIN, _LEGACY_UNIQUE_ID
    )
    if legacy_entity_id is not None:
        legacy_entry = registry.async_get(legacy_entity_id)
        if legacy_entry is not None and legacy_entry.config_entry_id == entry.entry_id:
            if registry.async_get_entity_id("binary_sensor", DOMAIN, sensor.unique_id) is None:
                registry.async_update_entity(
                    legacy_entity_id, new_unique_id=sensor.unique_id
                )
            else:
                _LOGGER.warning(
                    "Cannot migrate %s: unique ID %s already exists; preserving both registry entries",
                    legacy_entity_id, sensor.unique_id,
                )

    async_add_entities([
        sensor,
    ])

class StratasysOnlineBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of the printer's online status."""

    _attr_name = "Stratasys Printer Online"
    _attr_device_class = "connectivity"

    def __init__(self, coordinator, entry):
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.config_entry = entry
        self._attr_unique_id = f"{entry.entry_id}_printer_online"

    @property
    def is_on(self) -> bool:
        """Return True if the printer is considered online."""
        return (self.coordinator.data or {}).get("online", False)

    def _handle_coordinator_update(self) -> None:
        """Handle a coordinator update."""
        self.async_write_ha_state()

    @property
    def device_info(self):
        """Return device info to group it properly under the printer device."""
        model = (self.coordinator.data or {}).get("general", {}).get("modelerType", "Unknown Model")
        return {
            "identifiers": {(DOMAIN, self.config_entry.entry_id)},
            "name": "Stratasys 3D Printer",
            "manufacturer": "Stratasys",
            "model": model,
        }
