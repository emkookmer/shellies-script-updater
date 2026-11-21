"""Shellies Script Updater integration."""

import asyncio

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import SCRIPTS
from .coordinator import ScriptCoordinator

type ShelliesConfigEntry = ConfigEntry[tuple[ScriptCoordinator, ...]]

PLATFORMS = [Platform.UPDATE]


async def async_setup_entry(hass: HomeAssistant, entry: ShelliesConfigEntry) -> bool:
    """Start independent release checks for the two scripts."""
    reload_lock = asyncio.Lock()
    entry.runtime_data = tuple(
        ScriptCoordinator(hass, entry, script, reload_lock) for script in SCRIPTS
    )

    # Detect and record both installed versions before setting up the update entities.
    await asyncio.gather(*(item.async_initialize() for item in entry.runtime_data))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ShelliesConfigEntry) -> bool:
    """Unload the two update entities and stop their scheduled checks."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)