"""Sources for the two Shellies Discovery scripts."""

from dataclasses import dataclass
from datetime import timedelta

DOMAIN = "shellies_script_updater"
SCAN_INTERVAL = timedelta(hours=6)


@dataclass(frozen=True, slots=True)
class Script:
    """One managed script and its upstream release archive."""

    filename: str
    repository: str
    asset: str
    translation_key: str

    @property
    def github_url(self) -> str:
        """Return the upstream repository URL."""
        return f"https://github.com/bieniu/{self.repository}"


SCRIPTS = (
    Script(
        filename="shellies_discovery.py",
        repository="ha-shellies-discovery",
        asset="shellies-discovery.zip",
        translation_key="gen1",
    ),
    Script(
        filename="shellies_discovery_gen2.py",
        repository="ha-shellies-discovery-gen2",
        asset="shellies-discovery-gen2.zip",
        translation_key="gen2",
    ),
)