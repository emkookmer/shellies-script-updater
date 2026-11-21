"""Expose the two scripts as Home Assistant update entities."""

from typing import Any

from homeassistant.components.update import UpdateEntity, UpdateEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ShelliesConfigEntry
from .coordinator import MISSING, UNTRACKED, ScriptCoordinator

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ShelliesConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add one update entity per script."""
    async_add_entities(ShelliesScriptUpdate(item) for item in entry.runtime_data)


class ShelliesScriptUpdate(CoordinatorEntity[ScriptCoordinator], UpdateEntity):
    """Show the installed script version and allow manual updates."""

    _attr_has_entity_name = True
    _attr_supported_features = UpdateEntityFeature.INSTALL | UpdateEntityFeature.RELEASE_NOTES

    def __init__(self, coordinator: ScriptCoordinator) -> None:
        """Set identifiers for this script."""
        super().__init__(coordinator)
        self._attr_unique_id = coordinator.script.filename
        self._attr_translation_key = coordinator.script.translation_key
        self._attr_title = coordinator.script.filename

    @property
    def installed_version(self) -> str | None:
        """Return the local version or the displayed installation status."""
        return self.coordinator.data.installed if self.coordinator.data else None

    @property
    def latest_version(self) -> str | None:
        """Return the latest GitHub release tag."""
        return self.coordinator.data.release.tag if self.coordinator.data else None

    @property
    def release_url(self) -> str | None:
        """Link to the upstream release."""
        return self.coordinator.data.release.page if self.coordinator.data else None

    def version_is_newer(self, latest_version: str, installed_version: str) -> bool:
        """Offer installation for scripts without a known installed version."""
        if installed_version in (MISSING, UNTRACKED):
            return True
        latest = latest_version.removeprefix("v")
        installed = installed_version.removeprefix("v")
        return super().version_is_newer(latest, installed)

    async def async_release_notes(self) -> str | None:
        """Return the upstream release notes."""
        return self.coordinator.data.release.notes if self.coordinator.data else None

    async def async_install(self, version: str | None, backup: bool, **kwargs: Any) -> None:
        """Install the displayed release."""
        await self.coordinator.async_install(version)