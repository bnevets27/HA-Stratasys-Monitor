"""Connectivity identity regressions with process-isolated Home Assistant stubs."""

import unittest

if __name__ != "__main__":
    import subprocess
    import sys

    class IsolatedBinarySensorTests(unittest.TestCase):
        def test_binary_sensor_in_separate_process(self):
            result = subprocess.run(
                [sys.executable, "-B", __file__], capture_output=True, text=True
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

else:
    from pathlib import Path
    import sys
    import types
    from unittest.mock import Mock

    root = Path(__file__).resolve().parents[1] / "custom_components" / "stratasys"
    for name in (
        "homeassistant", "homeassistant.components",
        "homeassistant.components.binary_sensor", "homeassistant.helpers",
        "homeassistant.helpers.entity_registry",
        "homeassistant.helpers.update_coordinator", "homeassistant.core",
        "homeassistant.config_entries", "custom_components",
        "custom_components.stratasys",
    ):
        sys.modules[name] = types.ModuleType(name)
    sys.modules["custom_components.stratasys"].__path__ = [str(root)]

    class CoordinatorEntity:
        def __init__(self, coordinator):
            self.coordinator = coordinator

    class BinarySensorEntity:
        @property
        def unique_id(self):
            return self._attr_unique_id

    sys.modules["homeassistant.components.binary_sensor"].BinarySensorEntity = BinarySensorEntity
    sys.modules["homeassistant.helpers.update_coordinator"].CoordinatorEntity = CoordinatorEntity
    sys.modules["homeassistant.core"].HomeAssistant = object
    sys.modules["homeassistant.config_entries"].ConfigEntry = object
    sys.modules["homeassistant.helpers.entity_registry"].async_get = lambda hass: hass.registry

    from custom_components.stratasys.binary_sensor import async_setup_entry

    class Registry:
        """Small registry double enforcing domain/platform/unique-ID identity."""

        def __init__(self):
            self.entries = {}
            self.updates = []

        def add(self, entity_id, unique_id, owner, platform="stratasys"):
            entry = types.SimpleNamespace(
                entity_id=entity_id, unique_id=unique_id, config_entry_id=owner,
                platform=platform, name="Custom printer name", disabled_by="user",
                area_id="workshop", icon="mdi:printer-3d", hidden_by="user",
            )
            self.entries[entity_id] = entry
            return entry

        def async_get_entity_id(self, domain, platform, unique_id):
            return next((e.entity_id for e in self.entries.values()
                         if e.entity_id.split(".")[0] == domain
                         and e.platform == platform and e.unique_id == unique_id), None)

        def async_get(self, entity_id):
            return self.entries.get(entity_id)

        def async_update_entity(self, entity_id, *, new_unique_id):
            entry = self.entries[entity_id]
            if self.async_get_entity_id("binary_sensor", entry.platform, new_unique_id):
                raise ValueError("Duplicate unique ID")
            self.updates.append((entity_id, new_unique_id))
            entry.unique_id = new_unique_id
            return entry

    class BinarySensorTests(unittest.IsolatedAsyncioTestCase):
        def setUp(self):
            self.registry = Registry()
            self.coordinator = types.SimpleNamespace(data={"online": True})
            self.hass = types.SimpleNamespace(
                registry=self.registry,
                data={"stratasys": {"first": self.coordinator, "second": self.coordinator}},
            )

        async def setup_sensor(self, owner):
            added = []
            await async_setup_entry(
                self.hass, types.SimpleNamespace(entry_id=owner), added.extend
            )
            self.assertEqual(len(added), 1)
            return added[0]

        async def test_fresh_printers_have_distinct_stable_ids(self):
            first = await self.setup_sensor("first")
            second = await self.setup_sensor("second")
            self.assertEqual(first.unique_id, "first_printer_online")
            self.assertEqual(second.unique_id, "second_printer_online")
            self.assertEqual((await self.setup_sensor("first")).unique_id, first.unique_id)
            self.assertEqual(self.registry.updates, [])

        async def test_migration_preserves_record_and_customizations_before_add(self):
            legacy = self.registry.add(
                "binary_sensor.my_printer", "stratasys_printer_online", "first"
            )
            original = vars(legacy).copy()

            def add(entities):
                self.assertEqual(legacy.unique_id, entities[0].unique_id)

            await async_setup_entry(self.hass, types.SimpleNamespace(entry_id="first"), add)
            self.assertIs(self.registry.entries[legacy.entity_id], legacy)
            self.assertEqual(vars(legacy), {**original, "unique_id": "first_printer_online"})
            await self.setup_sensor("first")
            self.assertEqual(self.registry.updates, [(legacy.entity_id, "first_printer_online")])

        async def test_two_printer_setup_orders_preserve_ownership(self):
            for order in (("first", "second"), ("second", "first")):
                with self.subTest(order=order):
                    self.registry.entries.clear()
                    self.registry.updates.clear()
                    legacy = self.registry.add(
                        "binary_sensor.original", "stratasys_printer_online", "first"
                    )
                    for owner in order:
                        sensor = await self.setup_sensor(owner)
                        self.assertEqual(sensor.unique_id, f"{owner}_printer_online")
                        if owner == "second" and not self.registry.updates:
                            self.assertEqual(legacy.unique_id, "stratasys_printer_online")
                    self.assertEqual(self.registry.updates, [(legacy.entity_id, "first_printer_online")])
                    self.assertEqual(legacy.config_entry_id, "first")

        async def test_unowned_legacy_record_is_not_claimed(self):
            legacy = self.registry.add("binary_sensor.orphan", "stratasys_printer_online", None)
            await self.setup_sensor("first")
            self.assertEqual(legacy.unique_id, "stratasys_printer_online")
            self.assertEqual(self.registry.updates, [])

        async def test_collision_logs_and_preserves_both_records(self):
            self.registry.add("binary_sensor.old", "stratasys_printer_online", "first")
            self.registry.add("binary_sensor.new", "first_printer_online", "first")
            original = {key: vars(value).copy() for key, value in self.registry.entries.items()}
            with self.assertLogs("custom_components.stratasys.binary_sensor", level="WARNING"):
                sensor = await self.setup_sensor("first")
            self.assertEqual(sensor.unique_id, "first_printer_online")
            self.assertEqual(self.registry.updates, [])
            self.assertEqual({key: vars(value) for key, value in self.registry.entries.items()}, original)

        async def test_lookup_does_not_migrate_other_domains_or_platforms(self):
            self.registry.add("sensor.online", "stratasys_printer_online", "first")
            self.registry.add("binary_sensor.other", "stratasys_printer_online", "first", "other")
            await self.setup_sensor("first")
            self.assertEqual(self.registry.updates, [])

        async def test_connectivity_and_device_identity_are_unchanged(self):
            sensor = await self.setup_sensor("first")
            self.assertTrue(sensor.is_on)
            self.coordinator.data = {"online": False}
            self.assertFalse(sensor.is_on)
            self.coordinator.data = None
            self.assertFalse(sensor.is_on)
            self.assertEqual(sensor.device_info["identifiers"], {("stratasys", "first")})
            sensor.async_write_ha_state = Mock()
            sensor._handle_coordinator_update()
            sensor.async_write_ha_state.assert_called_once_with()

    unittest.main()
