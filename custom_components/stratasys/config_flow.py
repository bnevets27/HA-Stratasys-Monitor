import voluptuous as vol
from homeassistant import config_entries
from .const import DOMAIN

DEFAULT_SCAN_INTERVAL = 30  # seconds

class StratasysPrinterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            return self.async_create_entry(
                title=user_input["host"],
                data=user_input
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("host"): str,
                vol.Required("port", default=53742): int,
                vol.Required("scan_interval", default=DEFAULT_SCAN_INTERVAL): vol.All(int, vol.Range(min=5, max=600)),
            }),
            errors=errors
        )
