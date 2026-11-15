"""Stratasys Printer Switch Controls."""

import asyncio
import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
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
        self._command_lock = asyncio.Lock()

        # Entity configuration
        self._attr_name = "Door Lock"
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
        door_latch_state = (self._coordinator.data or {}).get("mariner", {}).get("doorLatch")
        if door_latch_state is None:
            return None
        # Convert to boolean - assuming the sensor returns True when latched/locked
        if isinstance(door_latch_state, bool):
            return door_latch_state
        if isinstance(door_latch_state, (str, int)):
            return {"0": False, "1": True, "false": False, "true": True}.get(
                str(door_latch_state).lower()
            )
        return None

    @property
    def available(self) -> bool:
        """Return True when a recent printer status was obtained."""
        return self._coordinator.last_update_success and bool(
            (self._coordinator.data or {}).get("online", False)
        )

    async def _set_latch(self, desired: bool) -> None:
        async with self._command_lock:
            await self._coordinator.async_refresh()
            if not self.available:
                raise HomeAssistantError("Printer is offline")
            if self.is_on is None:
                raise HomeAssistantError("Cannot set door lock: current state is unknown")
            if self.is_on != desired:
                await self._toggle_door_latch()
                self._verify_state(desired)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Lock the door latch."""
        await self._set_latch(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Unlock the door latch."""
        await self._set_latch(False)

    async def async_toggle(self, **kwargs: Any) -> None:
        """Toggle the door latch."""
        async with self._command_lock:
            await self._coordinator.async_refresh()
            if not self.available or self.is_on is None:
                raise HomeAssistantError("Cannot toggle door lock: current state is unknown")
            desired = not self.is_on
            await self._toggle_door_latch()
            self._verify_state(desired)

    def _verify_state(self, desired: bool) -> None:
        if not self.available or self.is_on is None:
            raise HomeAssistantError("Door lock command sent, but its result could not be verified")
        if self.is_on != desired:
            raise HomeAssistantError("Printer did not report the requested door lock state")

    async def _toggle_door_latch(self) -> None:
        """Toggle the latch and refresh the actual state after it settles."""
        if not self.available:
            raise HomeAssistantError("Printer is offline")
        if not await self._coordinator.monitor.toggle_door_latch():
            raise HomeAssistantError("Printer door lock command failed")
        await asyncio.sleep(2)
        await self._coordinator.async_refresh()
