"""Track and install one Shellies Discovery script."""

import asyncio
from dataclasses import dataclass, replace
from hashlib import sha256
import logging
import os
from pathlib import Path
from stat import S_ISREG
from tempfile import NamedTemporaryFile
from zipfile import BadZipFile

from aiohttp import ClientError

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, SCAN_INTERVAL, Script
from .release import (
    MAX_BYTES,
    Release,
    async_download_archive,
    async_latest_release,
    script_version,
    verified_script,
)

_LOGGER = logging.getLogger(__name__)

MISSING = "Not installed"
UNTRACKED = "Untracked"


@dataclass(frozen=True, slots=True)
class ScriptStatus:
    """Current local version and available release."""

    installed: str
    release: Release


class ScriptCoordinator(DataUpdateCoordinator[ScriptStatus]):
    """Keep the release and its installed version in sync."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        script: Script,
        reload_lock: asyncio.Lock,
    ) -> None:
        """Initialize a coordinator for one upstream repository."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=script.repository,
            update_interval=SCAN_INTERVAL,
            always_update=False,
        )
        self.script = script
        self.path = Path(hass.config.path("python_scripts", script.filename))
        self.session = async_get_clientsession(hass)
        self.store: Store[dict[str, str]] = Store(
            hass, 1, f"{DOMAIN}.{script.translation_key}", atomic_writes=True
        )
        self.installed: dict[str, str] | None = None
        self.lock = asyncio.Lock()
        self.reload_lock = reload_lock

    async def async_initialize(self) -> None:
        """Detect the installed version on setup and check the latest release."""
        self.installed = await self.store.async_load()
        await self.async_refresh()

    async def _async_update_data(self) -> ScriptStatus:
        """Check GitHub and reconcile the version with the file on disk."""
        async with self.lock:
            try:
                content, _ = await self.hass.async_add_executor_job(
                    _read_script, self.path
                )
                installed = await self._async_record_version(content)
                release = await async_latest_release(self.session, self.script)
            except (ClientError, OSError, TimeoutError, ValueError, KeyError, TypeError) as err:
                raise UpdateFailed(str(err)) from err
            return ScriptStatus(installed, release)

    async def _async_record_version(
        self, content: bytes | None, version: str | None = None
    ) -> str:
        """Persist the version and hash only for a recognized file."""
        record = None
        if content is not None:
            digest = sha256(content).hexdigest()
            if self.installed and self.installed.get("sha256") == digest and version is None:
                return self.installed["version"]
            if version := version or script_version(content):
                record = {"version": version, "sha256": digest}

        if record != self.installed:
            if record is None:
                await self.store.async_remove()
            else:
                await self.store.async_save(record)
            self.installed = record

        if record is not None:
            return record["version"]
        return MISSING if content is None else UNTRACKED

    async def async_install(self, version: str | None) -> None:
        """Install the release currently shown in Home Assistant."""
        async with self.lock:
            if not self.last_update_success or self.data is None:
                raise HomeAssistantError("The latest release check failed. Try again later.")
            release = self.data.release
            if version is not None and version != release.tag:
                raise HomeAssistantError("Only the displayed release can be installed.")

            try:
                archive = await async_download_archive(self.session, release)
                content = await self.hass.async_add_executor_job(
                    verified_script, archive, release, self.script
                )
                await self.hass.async_add_executor_job(
                    _install_script, self.path, content, release.tag
                )
            except (
                BadZipFile, ClientError, KeyError, OSError, RuntimeError,
                SyntaxError, TimeoutError, ValueError,
            ) as err:
                raise HomeAssistantError(
                    f"Could not install {self.script.filename}: {err}"
                ) from err

            try:
                await self._async_record_version(content, release.tag)
            except (HomeAssistantError, OSError) as err:
                # A later poll can recover the version from the installed file.
                _LOGGER.warning("Could not store the installed version: %s", err)
            self.async_set_updated_data(replace(self.data, installed=release.tag))

        async with self.reload_lock:
            if (
                self.hass.services.has_service("python_script", "reload")
                and not self.hass.services.has_service("python_script", self.path.stem)
            ):
                try:
                    await self.hass.services.async_call(
                        "python_script", "reload", blocking=True
                    )
                except HomeAssistantError as err:
                    _LOGGER.warning("Could not reload Python Scripts: %s", err)


def _read_script(path: Path) -> tuple[bytes | None, int]:
    """Read a regular script and its permissions, or return the mode for a new file."""
    if path.parent.is_symlink():
        raise ValueError(f"{path.parent} must be a regular directory")
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        return None, 0o644
    if not S_ISREG(mode):
        raise ValueError(f"{path} must be a regular file")
    with path.open("rb") as source:
        content = source.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        raise ValueError(f"{path} exceeds the supported size limit")
    return content, mode & 0o777


def _install_script(path: Path, content: bytes, version: str) -> None:
    """Atomically replace the script after checking its installed version."""
    previous, mode = _read_script(path)
    if previous == content:
        return
    installed = script_version(previous) if previous is not None else None
    if installed and _version_parts(installed) > _version_parts(version):
        raise ValueError(f"The installed script version {installed} is newer than {version}")
    path.parent.mkdir(exist_ok=True)
    _atomic_write(path, content, mode)


def _version_parts(version: str) -> tuple[int, ...]:
    """Compare the numeric parts of an upstream release tag."""
    return tuple(int(part) for part in version.removeprefix("v").split("."))


def _atomic_write(path: Path, content: bytes, mode: int) -> None:
    """Set permissions on the staged file before replacing the original."""
    with NamedTemporaryFile(dir=path.parent, delete=False) as staged:
        temporary = Path(staged.name)
        try:
            staged.write(content)
            staged.close()
            temporary.chmod(mode)
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)