"""Focused tests with minimal Home Assistant stubs; run in a separate process."""

import asyncio
from pathlib import Path
from datetime import timedelta
from enum import StrEnum
import sys
import types
import unittest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# The integration has no local Home Assistant dependency. Isolate these stubs by
# running this module as a standalone process, not through test discovery.
for name in (
    "homeassistant", "homeassistant.config_entries", "homeassistant.core",
    "homeassistant.exceptions", "homeassistant.helpers",
    "homeassistant.helpers.update_coordinator", "homeassistant.helpers.entity_platform",
    "homeassistant.components", "homeassistant.components.light",
    "homeassistant.components.switch",
):
    sys.modules[name] = types.ModuleType(name)


class CoordinatorStub:
    def __init__(self, hass, logger, *, name, update_interval, config_entry):
        self.update_interval = update_interval
        self.last_update_success = True
        self.data = None


class UpdateFailed(Exception):
    pass


class EntityStub:
    def __init__(self, coordinator):
        self.coordinator = coordinator


class LightStub:
    pass


class ColorMode(StrEnum):
    ONOFF = "onoff"


class SwitchStub:
    pass


class HAError(Exception):
    pass


for module, name, value in (
    ("config_entries", "ConfigEntry", object), ("core", "HomeAssistant", object),
    ("exceptions", "HomeAssistantError", HAError),
    ("helpers.update_coordinator", "DataUpdateCoordinator", CoordinatorStub),
    ("helpers.update_coordinator", "UpdateFailed", UpdateFailed),
    ("helpers.update_coordinator", "CoordinatorEntity", EntityStub),
    ("helpers.entity_platform", "AddEntitiesCallback", object),
    ("components.light", "LightEntity", LightStub),
    ("components.light", "ColorMode", ColorMode),
    ("components.switch", "SwitchEntity", SwitchStub),
):
    setattr(sys.modules["homeassistant." + module], name, value)

from custom_components.stratasys.coordinator import PrinterDataCoordinator
from custom_components.stratasys.printer import (
    ConnectionError as PrinterConnectionError, PrinterConfig, ProtocolError, StratasysMonitor,
)
from custom_components.stratasys.light import StratasysLight, async_setup_entry as setup_light
from custom_components.stratasys.switch import StratasyssDoorLatchSwitch


class IntegrationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.monitor = types.SimpleNamespace(
            get_status=AsyncMock(), turn_light_on=AsyncMock(return_value=True),
            turn_light_off=AsyncMock(return_value=True), toggle_light=AsyncMock(return_value=True),
            toggle_door_latch=AsyncMock(return_value=True),
        )
        entry = types.SimpleNamespace(entry_id="test", title="printer")
        self.coordinator = PrinterDataCoordinator(None, entry, self.monitor, 30)
        self.coordinator.data = {"online": True, "mariner": {"lightsOn": 0, "doorLatch": 0}}
        self.coordinator.async_refresh = AsyncMock()
        self.light = StratasysLight(self.coordinator, entry)
        self.door = StratasyssDoorLatchSwitch(self.coordinator, entry)
        self.sleep = patch("asyncio.sleep", new=AsyncMock())
        self.sleep.start()
        self.addCleanup(self.sleep.stop)

    async def test_light_setup_preserves_identity_and_declares_onoff_mode(self):
        entry = types.SimpleNamespace(entry_id="test", title="192.168.1.28")
        hass = types.SimpleNamespace(data={"stratasys": {entry.entry_id: self.coordinator}})
        entities = []
        await setup_light(hass, entry, entities.extend)
        self.assertEqual(len(entities), 1)
        light = entities[0]
        self.assertEqual(light._attr_unique_id, "test_light")
        self.assertEqual(light._attr_supported_color_modes, {ColorMode.ONOFF})
        self.assertEqual(light._attr_color_mode, ColorMode.ONOFF)
        self.assertTrue(light.available)
        self.assertFalse(light.is_on)

    async def test_offline_and_recovery(self):
        self.monitor.get_status.side_effect = [OSError(), OSError(), {"mariner": {"lightsOn": 0}}]
        for _ in range(2):
            self.assertEqual(await self.coordinator._async_update_data(), {"online": False})
            self.assertEqual(self.coordinator.update_interval, timedelta(minutes=5))
        self.assertTrue((await self.coordinator._async_update_data())["online"])
        self.assertEqual(self.coordinator.update_interval, timedelta(seconds=30))

    async def test_invalid_status_and_unexpected_failure_are_visible(self):
        for result in ({}, {"bad": 1}):
            self.monitor.get_status.return_value = result
            with self.assertRaises(UpdateFailed):
                await self.coordinator._async_update_data()
        self.monitor.get_status.side_effect = RuntimeError("bug")
        with self.assertRaisesRegex(RuntimeError, "bug"):
            await self.coordinator._async_update_data()

    async def test_repeated_offline_connects_are_quiet_and_close_sockets(self):
        monitor = StratasysMonitor(PrinterConfig(host="offline", port=1, retry_attempts=2))
        sock = unittest.mock.MagicMock()
        sock.connect.side_effect = TimeoutError("timed out")
        self.coordinator.monitor = monitor
        with patch("custom_components.stratasys.printer.socket",
                   types.SimpleNamespace(socket=lambda *args: sock, AF_INET=2, SOCK_STREAM=1)):
            with self.assertLogs("custom_components.stratasys", level="DEBUG") as logs:
                for _ in range(2):
                    self.assertEqual(await self.coordinator._async_update_data(), {"online": False})
        self.assertEqual(sock.close.call_count, 4)
        self.assertFalse(any(record.levelno >= 30 for record in logs.records))

    async def test_eof_during_protocol_is_offline(self):
        monitor = StratasysMonitor(PrinterConfig(host="offline", port=1, retry_attempts=1))
        for packets in ([b""], [b"SendFile".ljust(64, b"\x00"),
                               b"NA".ljust(64, b"\x00"),
                               b"20".ljust(64, b"\x00"), b"partial", b""]):
            sock = unittest.mock.MagicMock()
            sock.recv.side_effect = packets
            monitor.sock = sock
            with self.assertRaises(PrinterConnectionError):
                await monitor._get_printer_data()

    async def test_nonempty_malformed_protocol_remains_visible(self):
        monitor = StratasysMonitor(PrinterConfig(host="offline", port=1))
        monitor.sock = unittest.mock.MagicMock()
        monitor.sock.recv.return_value = b"unexpected"
        with self.assertRaises(ProtocolError):
            await monitor._get_printer_data()

    async def test_commands_confirm_reported_state_and_serialize_door(self):
        async def refresh():
            if self.monitor.turn_light_on.await_count:
                self.coordinator.data["mariner"]["lightsOn"] = 1
            if self.monitor.toggle_door_latch.await_count:
                self.coordinator.data["mariner"]["doorLatch"] = 1
        self.coordinator.async_refresh.side_effect = refresh
        await self.light.async_turn_on()
        await asyncio.gather(self.door.async_turn_on(), self.door.async_turn_on())
        self.assertTrue(self.light.is_on)
        self.assertTrue(self.door.is_on)
        self.assertEqual(self.monitor.toggle_door_latch.await_count, 1)

    async def test_unknown_and_mismatch_fail_verification(self):
        with self.assertRaisesRegex(HAError, "requested light state"):
            await self.light.async_turn_on()
        with self.assertRaisesRegex(HAError, "requested door lock state"):
            await self.door.async_turn_on()
        async def lose_status():
            self.coordinator.data = {"online": False}
        self.coordinator.async_refresh.side_effect = lose_status
        with self.assertRaisesRegex(HAError, "could not be verified"):
            await self.light.async_turn_on()
        self.coordinator.data = {"online": True, "mariner": {"doorLatch": 0}}
        calls = 0
        async def lose_after_command():
            nonlocal calls
            calls += 1
            if calls == 2:
                self.coordinator.data = {"online": True, "mariner": {}}
        self.coordinator.async_refresh.side_effect = lose_after_command
        with self.assertRaisesRegex(HAError, "could not be verified"):
            await self.door.async_turn_on()

    async def test_toggles_require_known_state_and_verify(self):
        self.coordinator.data["mariner"] = {}
        with self.assertRaises(HAError):
            await self.light.async_toggle()
        with self.assertRaises(HAError):
            await self.door.async_toggle()
        self.monitor.toggle_light.assert_not_awaited()
        self.monitor.toggle_door_latch.assert_not_awaited()
        self.coordinator.data["mariner"] = {"lightsOn": 0, "doorLatch": 0}
        with self.assertRaisesRegex(HAError, "requested light state"):
            await self.light.async_toggle()
        with self.assertRaisesRegex(HAError, "requested door lock state"):
            await self.door.async_toggle()


if __name__ == "__main__":
    unittest.main()
