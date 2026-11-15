"""Stratasys Printer Light Control."""

import logging
import asyncio
from typing import Any

from homeassistant.components.light import ColorMode, LightEntity
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
    """Set up Stratasys light entities."""
    coordinator: PrinterDataCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = [
        StratasysLight(coordinator, config_entry),
    ]

    async_add_entities(entities)


class StratasysLight(CoordinatorEntity, LightEntity):
    """Stratasys printer chamber light control."""

    _attr_color_mode = ColorMode.ONOFF
    _attr_supported_color_modes = {ColorMode.ONOFF}

    def __init__(self, coordinator: PrinterDataCoordinator, config_entry: ConfigEntry) -> None:
        """Initialize the light."""
        super().__init__(coordinator)
        self._coordinator = coordinator
        self._config_entry = config_entry
        self._command_lock = asyncio.Lock()

        # Entity configuration
        self._attr_name = "Chamber Light"
        self._attr_unique_id = f"{config_entry.entry_id}_light"
        self._attr_icon = "mdi:lightbulb"

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
        """Return True if the chamber light is on."""
        lights_on = (self._coordinator.data or {}).get("mariner", {}).get("lightsOn")
        if lights_on is None:
            return None
        if isinstance(lights_on, bool):
            return lights_on
        if isinstance(lights_on, (str, int)):
            return {"0": False, "1": True, "false": False, "true": True}.get(
                str(lights_on).lower()
            )
        return None

    @property
    def available(self) -> bool:
        """Return True when a recent printer status was obtained."""
        return self._coordinator.last_update_success and bool(
            (self._coordinator.data or {}).get("online", False)
        )

    async def _command(self, command, desired: bool | None = None) -> None:
        """Send a command and verify the state reported by the printer."""
        async with self._command_lock:
            if desired is None:
                await self._coordinator.async_refresh()
                if not self.available or self.is_on is None:
                    raise HomeAssistantError("Cannot toggle light: current state is unknown")
                desired = not self.is_on
            if not self.available:
                raise HomeAssistantError("Printer is offline")
            if not await command():
                raise HomeAssistantError("Printer light command failed")
            await asyncio.sleep(2)
            await self._coordinator.async_refresh()
            if not self.available or self.is_on is None:
                raise HomeAssistantError("Light command sent, but its result could not be verified")
            if self.is_on != desired:
                raise HomeAssistantError("Printer did not report the requested light state")

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the chamber light on."""
        await self._command(self._coordinator.monitor.turn_light_on, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the chamber light off."""
        await self._command(self._coordinator.monitor.turn_light_off, False)

    async def async_toggle(self, **kwargs: Any) -> None:
        """Toggle the chamber light."""
        await self._command(self._coordinator.monitor.toggle_light)
