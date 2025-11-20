"""Stratasys Printer Light Control."""

import logging
from typing import Any

from homeassistant.components.light import LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import PrinterDataCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Stratasys light entities."""
    coordinator: PrinterDataCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    entities = [
        StratasysLight(coordinator, config_entry),
    ]
    
    async_add_entities(entities)


class StratasysLight(LightEntity):
    """Stratasys printer light control."""

    def __init__(self, coordinator: PrinterDataCoordinator, config_entry: ConfigEntry) -> None:
        """Initialize the light."""
        self._coordinator = coordinator
        self._config_entry = config_entry
        
        # Entity configuration
        self._attr_name = f"{config_entry.title} Light"
        self._attr_unique_id = f"{config_entry.entry_id}_light"
        
        # Device information
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": config_entry.title,
            "manufacturer": "Stratasys",
            "model": "3D Printer",
            "sw_version": "1.0.6",
        }

    @property
    def is_on(self) -> bool | None:
        """Return True if the light is on."""
        # Since we can't query the current light state from the printer,
        # we'll assume it's off by default. This could be enhanced in the future
        # if there's a way to read the light status from the printer.
        return None  # Unknown state
        
    @property
    def available(self) -> bool:
        """Return True if the light is available."""
        return self._coordinator.last_update_success

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        try:
            success = await self._coordinator.monitor.turn_light_on()
            if success:
                _LOGGER.info("Successfully turned on printer light")
                # Force a coordinator update to refresh entity states
                await self._coordinator.async_request_refresh()
            else:
                _LOGGER.error("Failed to turn on printer light")
        except Exception as e:
            _LOGGER.error(f"Error turning on printer light: {e}")
            raise

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        try:
            success = await self._coordinator.monitor.turn_light_off()
            if success:
                _LOGGER.info("Successfully turned off printer light")
                # Force a coordinator update to refresh entity states
                await self._coordinator.async_request_refresh()
            else:
                _LOGGER.error("Failed to turn off printer light")
        except Exception as e:
            _LOGGER.error(f"Error turning off printer light: {e}")
            raise

    async def async_toggle(self, **kwargs: Any) -> None:
        """Toggle the light."""
        try:
            success = await self._coordinator.monitor.toggle_light()
            if success:
                _LOGGER.info("Successfully toggled printer light")
                # Force a coordinator update to refresh entity states
                await self._coordinator.async_request_refresh()
            else:
                _LOGGER.error("Failed to toggle printer light")
        except Exception as e:
            _LOGGER.error(f"Error toggling printer light: {e}")
            raise