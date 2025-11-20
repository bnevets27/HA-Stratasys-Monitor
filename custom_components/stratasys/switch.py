"""Stratasys Printer Switch Controls."""

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PrinterDataCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Stratasys switch entities."""
    coordinator: PrinterDataCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    entities = [
        StratasyssDoorLatchSwitch(coordinator, config_entry),
    ]
    
    async_add_entities(entities)


class StratasyssDoorLatchSwitch(CoordinatorEntity, SwitchEntity):
    """Stratasys printer door latch lock/unlock switch."""

    def __init__(self, coordinator: PrinterDataCoordinator, config_entry: ConfigEntry) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._coordinator = coordinator
        self._config_entry = config_entry
        
        # Entity configuration
        self._attr_name = f"{config_entry.title} Door Lock"
        self._attr_unique_id = f"{config_entry.entry_id}_door_lock"
        self._attr_icon = "mdi:lock"
        
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
        """Return True if the door latch is locked (engaged)."""
        # Get the door latch state from the coordinator data
        door_latch_state = self._coordinator.data.get("mariner", {}).get("doorLatch")
        if door_latch_state is None:
            return None
        # Convert to boolean - assuming the sensor returns True when latched/locked
        return bool(door_latch_state)
        
    @property
    def available(self) -> bool:
        """Return True if the switch is available."""
        return self._coordinator.last_update_success

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Lock the door latch."""
        current_state = self.is_on
        # Only toggle if we need to change state (current is False/unlocked and we want True/locked)
        if current_state is False:
            await self._toggle_door_latch()
        elif current_state is None:
            # Unknown state, send toggle command anyway
            await self._toggle_door_latch()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Unlock the door latch."""
        current_state = self.is_on
        # Only toggle if we need to change state (current is True/locked and we want False/unlocked)
        if current_state is True:
            await self._toggle_door_latch()
        elif current_state is None:
            # Unknown state, send toggle command anyway
            await self._toggle_door_latch()

    async def async_toggle(self, **kwargs: Any) -> None:
        """Toggle the door latch."""
        await self._toggle_door_latch()

    async def _toggle_door_latch(self) -> None:
        """Internal method to toggle the door latch lock state."""
        try:
            success = await self._coordinator.monitor.toggle_door_latch()
            if success:
                _LOGGER.info("Successfully toggled printer door lock")
                # Force a coordinator update to refresh entity states and get new lock state
                await self._coordinator.async_request_refresh()
            else:
                _LOGGER.error("Failed to toggle printer door lock")
        except Exception as e:
            _LOGGER.error(f"Error toggling printer door lock: {e}")
            raise