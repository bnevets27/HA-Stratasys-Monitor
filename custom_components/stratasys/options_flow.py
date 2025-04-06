"""Options flow for Stratasys Printer integration."""

import voluptuous as vol
from homeassistant import config_entries
from .const import DOMAIN

DEFAULT_SCAN_INTERVAL = 30

class StratasysOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Stratasys Printer."""

    def __init__(self, config_entry: config_entries.ConfigEntry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_interval = self.config_entry.options.get(
            "scan_interval", self.config_entry.data.get("scan_interval", DEFAULT_SCAN_INTERVAL)
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required("scan_interval", default=current_interval): vol.All(int, vol.Range(min=5, max=600))
            })
        )
