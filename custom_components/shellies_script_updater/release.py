"""Fetch and verify published Shellies Discovery releases."""

from codecs import BOM_UTF8
from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
import re
from zipfile import ZipFile

from aiohttp import ClientSession, ClientTimeout

from .const import Script

MAX_BYTES = 1024 * 1024
_TIMEOUT = ClientTimeout(total=30)
_TAG = re.compile(r"v?\d+\.\d+\.\d+")
_VERSION = re.compile(
    rb"""^VERSION[ \t]*=[ \t]*(?P<quote>["'])(?P<version>v?\d+\.\d+\.\d+)(?P=quote)[ \t]*(?:#[^\r\n]*)?\r?$""",
    re.MULTILINE,
)


@dataclass(frozen=True, slots=True)
class Release:
    """An upstream release and its verified download metadata."""

    tag: str
    notes: str
    page: str
    archive: str
    digest: str


async def async_latest_release(session: ClientSession, script: Script) -> Release:
    """Read the latest stable release and locate its expected ZIP."""
    url = f"https://api.github.com/repos/bieniu/{script.repository}/releases/latest"
    async with session.get(
        url, timeout=_TIMEOUT, headers={"Accept": "application/vnd.github+json"}
    ) as response:
        response.raise_for_status()
        payload = await response.json()

    tag = payload["tag_name"]
    if not _TAG.fullmatch(tag):
        raise ValueError("Unexpected upstream release tag")

    for asset in payload["assets"]:
        if asset["name"] == script.asset:
            digest = asset.get("digest") or ""
            if not re.fullmatch(r"sha256:[a-f0-9]{64}", digest):
                raise ValueError("GitHub did not supply a SHA-256 digest for the release ZIP")
            page = f"{script.github_url}/releases"
            return Release(
                tag=tag,
                notes=payload.get("body") or "",
                page=f"{page}/tag/{tag}",
                archive=f"{page}/download/{tag}/{script.asset}",
                digest=digest.removeprefix("sha256:"),
            )
    raise ValueError(f"Upstream release has no {script.asset}")


async def async_download_archive(session: ClientSession, release: Release) -> bytes:
    """Download the published archive with a bounded response size."""
    archive = bytearray()
    async with session.get(release.archive, timeout=_TIMEOUT) as response:
        response.raise_for_status()
        async for chunk in response.content.iter_chunked(64 * 1024):
            archive.extend(chunk)
            if len(archive) > MAX_BYTES:
                raise ValueError("Release ZIP exceeds the size limit")
    return bytes(archive)


def script_version(content: bytes) -> str | None:
    """Read a release version stamped into an upstream script."""
    if match := _VERSION.search(content.removeprefix(BOM_UTF8)[:4096]):
        version = match["version"].decode("ascii")
        if version.removeprefix("v") != "0.0.0":
            return version
    return None


def verified_script(archive: bytes, release: Release, script: Script) -> bytes:
    """Verify the ZIP and return only the expected Python script."""
    if sha256(archive).hexdigest() != release.digest:
        raise ValueError("Release ZIP does not match GitHub's SHA-256 digest")

    with ZipFile(BytesIO(archive)) as package:
        info = package.getinfo(script.filename)
        if not 0 < info.file_size <= MAX_BYTES:
            raise ValueError("Unexpected script size in the release ZIP")
        with package.open(info) as source:
            content = source.read(MAX_BYTES + 1)

    version = script_version(content)
    if version is None or version.removeprefix("v") != release.tag.removeprefix("v"):
        raise ValueError("Script version does not match the release tag")
    compile(content, script.filename, "exec")
    return content