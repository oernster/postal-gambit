"""The update check's pure logic: version comparison, assets and the service.

Postal Gambit's standing claim is that the app itself never touches the
network; the one disclosed exception is the update check, whose network
half lives in a single exempt infrastructure module behind the
``ReleaseSource`` port. Everything here is pure: given a release, decide
whether it is newer, whether the user already skipped it and which asset
suits the running platform.
"""

from __future__ import annotations

from postalgambit.application.dto import ReleaseAsset, UpdateStatus
from postalgambit.application.ports import ReleaseSource

PLATFORM_KEY_WINDOWS = "windows"
PLATFORM_KEY_MACOS = "macos"
PLATFORM_KEY_LINUX = "linux"

_SYS_PLATFORM_KEYS = {
    "win32": PLATFORM_KEY_WINDOWS,
    "darwin": PLATFORM_KEY_MACOS,
}

_ASSET_SUFFIXES = {
    PLATFORM_KEY_WINDOWS: ".exe",
    PLATFORM_KEY_MACOS: ".dmg",
    PLATFORM_KEY_LINUX: ".flatpak",
}


def _version_tuple(text: str) -> tuple[int, ...] | None:
    """Parse ``text`` as a dotted integer tuple, else ``None``."""
    cleaned = text.strip()
    if cleaned[:1] in ("v", "V"):
        cleaned = cleaned[1:]
    try:
        return tuple(int(part) for part in cleaned.split("."))
    except ValueError:
        return None


def is_newer(candidate: str, current: str) -> bool:
    """Whether ``candidate`` names a strictly newer version.

    Anything unparseable compares as not newer, so a malformed tag can
    never raise a spurious prompt.
    """
    candidate_tuple = _version_tuple(candidate)
    current_tuple = _version_tuple(current)
    if candidate_tuple is None or current_tuple is None:
        return False
    return candidate_tuple > current_tuple


def platform_key_for(sys_platform: str) -> str:
    """Map a ``sys.platform`` value onto an asset platform key."""
    return _SYS_PLATFORM_KEYS.get(sys_platform, PLATFORM_KEY_LINUX)


def select_asset_url(assets: tuple[ReleaseAsset, ...], platform_key: str) -> str | None:
    """The download URL of the asset matching ``platform_key``, or None."""
    suffix = _ASSET_SUFFIXES.get(platform_key)
    if suffix is None:
        return None
    for asset in assets:
        if asset.name.lower().endswith(suffix):
            return asset.download_url
    return None


class UpdateService:
    """Asks the release source whether a newer version is published."""

    def __init__(
        self, source: ReleaseSource, current_version: str, platform_key: str
    ) -> None:
        self._source = source
        self._current = current_version
        self._platform_key = platform_key

    def check(self, skipped_version: str | None = None) -> UpdateStatus | None:
        """The check's conclusion, or ``None`` when the source is unreachable.

        A release equal to ``skipped_version`` is reported as seen but not
        available, which is what keeps a skipped version from prompting
        again on the automatic paths.
        """
        release = self._source.latest_release()
        if release is None:
            return None
        newer = is_newer(release.version, self._current)
        skipped = skipped_version is not None and release.version == skipped_version
        return UpdateStatus(
            current=self._current,
            latest=release.version,
            update_available=newer and not skipped,
            download_url=select_asset_url(release.assets, self._platform_key),
            page_url=release.page_url,
        )
