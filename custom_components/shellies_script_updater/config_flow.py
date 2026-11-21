"""Set up Shellies Script Updater from the Home Assistant UI."""

from typing import Any

from homeassistant import config_entries

from .const import DOMAIN


class ShelliesConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Add the two fixed upstream repositories in one config entry."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Create the singleton entry."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title="Shellies Script Updater", data={})