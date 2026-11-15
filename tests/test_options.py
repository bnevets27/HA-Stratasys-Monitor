"""Run the isolated options tests without leaking stubs into test discovery."""

if __name__ != "__main__":
    import subprocess
    import sys
    import unittest

    class IsolatedOptionsTests(unittest.TestCase):
        def test_options_in_separate_process(self):
            result = subprocess.run(
                [sys.executable, "-B", __file__], capture_output=True, text=True
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

else:
    """Options-flow compatibility checks; run this file in its own process."""

    import inspect
    from pathlib import Path
    import sys
    import types
    import unittest
    from unittest.mock import AsyncMock, Mock, patch

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

    for name in ("homeassistant", "homeassistant.config_entries", "homeassistant.core", "voluptuous"):
        sys.modules[name] = types.ModuleType(name)


    class ConfigFlow:
        def __init_subclass__(cls, **kwargs):
            pass


    class OptionsFlow:
        @property
        def config_entry(self):
            return self._config_entry

        def async_show_form(self, **kwargs):
            return kwargs

        def async_create_entry(self, **kwargs):
            return kwargs


    class Required:
        def __init__(self, name, default):
            self.name = name
            self.default = default


    def callback(func):
        func._is_callback = True
        return func


    ha_entries = sys.modules["homeassistant.config_entries"]
    ha_entries.ConfigEntry = object
    ha_entries.ConfigFlow = ConfigFlow
    ha_entries.OptionsFlow = OptionsFlow
    sys.modules["homeassistant"].config_entries = ha_entries
    sys.modules["homeassistant.core"].HomeAssistant = object
    sys.modules["homeassistant.core"].callback = callback
    vol = sys.modules["voluptuous"]
    vol.Required = Required
    vol.Schema = lambda schema: schema
    vol.All = lambda *args: args
    vol.Range = lambda **kwargs: kwargs

    # Avoid importing the real coordinator, which requires Home Assistant helpers.
    coordinator_module = types.ModuleType("custom_components.stratasys.coordinator")
    coordinator_module.PrinterDataCoordinator = object
    sys.modules[coordinator_module.__name__] = coordinator_module

    import custom_components.stratasys as integration
    from custom_components.stratasys.config_flow import StratasysPrinterConfigFlow
    from custom_components.stratasys.options_flow import StratasysOptionsFlowHandler


    class OptionsTests(unittest.IsolatedAsyncioTestCase):
        async def test_registered_sync_callback_and_form_defaults(self):
            registration = inspect.getattr_static(StratasysPrinterConfigFlow, "async_get_options_flow")
            self.assertIsInstance(registration, staticmethod)
            self.assertTrue(registration.__func__._is_callback)
            self.assertFalse(inspect.iscoroutinefunction(registration.__func__))
            entry = types.SimpleNamespace(options={}, data={"scan_interval": 45})
            flow = StratasysPrinterConfigFlow.async_get_options_flow(entry)
            self.assertIsInstance(flow, StratasysOptionsFlowHandler)
            flow._config_entry = entry  # HA owns the read-only property.
            form = await flow.async_step_init()
            self.assertEqual(next(iter(form["data_schema"])).default, 45)
            entry.options = {"scan_interval": 90}
            form = await flow.async_step_init()
            self.assertEqual(next(iter(form["data_schema"])).default, 90)
            self.assertEqual(await flow.async_step_init({"scan_interval": 60}),
                             {"title": "", "data": {"scan_interval": 60}})

        async def test_update_reloads_with_new_interval_and_removes_listener_on_unload(self):
            listeners, unload_callbacks, intervals = [], [], []
            entry = types.SimpleNamespace(entry_id="entry", data={"host": "printer", "port": 1, "scan_interval": 45}, options={})

            def add_listener(listener):
                listeners.append(listener)
                return lambda: listeners.remove(listener)

            entry.add_update_listener = add_listener
            entry.async_on_unload = unload_callbacks.append
            hass = types.SimpleNamespace(data={}, config_entries=types.SimpleNamespace(
                async_forward_entry_setups=AsyncMock(), async_unload_platforms=AsyncMock(return_value=True)))

            class Coordinator:
                def __init__(self, hass, entry, monitor, interval):
                    self.monitor = monitor
                    self.async_config_entry_first_refresh = AsyncMock()
                    intervals.append(interval)

            async def reload_entry(entry_id):
                self.assertEqual(entry_id, entry.entry_id)
                self.assertTrue(await integration.async_unload_entry(hass, entry))
                while unload_callbacks:
                    unload_callbacks.pop()()  # Home Assistant runs these after successful unload.
                self.assertTrue(await integration.async_setup_entry(hass, entry))

            hass.config_entries.async_reload = AsyncMock(side_effect=reload_entry)
            with patch.object(integration, "PrinterDataCoordinator", Coordinator), patch.object(integration, "StratasysMonitor") as monitor:
                self.assertTrue(await integration.async_setup_entry(hass, entry))
                entry.options = {"scan_interval": 60}
                await listeners[0](hass, entry)
                self.assertEqual(intervals, [45, 60])
                self.assertEqual(len(listeners), 1)
                monitor.return_value.cleanup.assert_called_once()
                hass.config_entries.async_reload.assert_awaited_once_with("entry")
                self.assertTrue(await integration.async_unload_entry(hass, entry))
                while unload_callbacks:
                    unload_callbacks.pop()()
                self.assertEqual(listeners, [])


    if __name__ == "__main__":
        unittest.main()
