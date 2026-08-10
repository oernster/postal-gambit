"""GitHub releases adapter: the one module exempt from the no-network rule.

Postal Gambit's product claim is that the mail client is the transport and
the app itself never touches the network. The single disclosed exception is
this module: one short, anonymous, best-effort HTTPS GET against the GitHub
releases API asking whether a newer published release exists. Nothing is
downloaded or run by the check itself and any failure reads as "no release
visible". The structural suite in ``tests/structural/test_no_network.py``
names this file as the sole exemption and fails if the exemption widens or
if this module stops being the reason for it.

The endpoint returns only published, non-draft, non-prerelease releases, so
a tag pushed mid-development can never surface here. The opener is injected
so tests never touch the network.
"""

from __future__ import annotations

import json
import urllib.request
from collections.abc import Callable
from typing import Any

from postalgambit.application.dto import ReleaseAsset, ReleaseInfo

RELEASES_LATEST_URL = (
    "https://api.github.com/repos/oernster/postal-gambit/releases/latest"
)
ACCEPT_HEADER = "application/vnd.github+json"
REQUEST_TIMEOUT_SECONDS = 5.0


def _default_opener(request: urllib.request.Request, timeout: float) -> Any:
    return urllib.request.urlopen(request, timeout=timeout)


def _parse_assets(raw: Any) -> tuple[ReleaseAsset, ...]:
    """The well-formed assets, with malformed entries silently dropped."""
    if not isinstance(raw, list):
        return ()
    assets = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        url = entry.get("browser_download_url")
        if isinstance(name, str) and name and isinstance(url, str) and url:
            assets.append(ReleaseAsset(name=name, download_url=url))
    return tuple(assets)


class GitHubReleaseSource:
    """Implements the ReleaseSource port over stdlib urllib."""

    def __init__(
        self,
        opener: Callable[[urllib.request.Request, float], Any] = _default_opener,
    ) -> None:
        self._opener = opener

    def latest_release(self) -> ReleaseInfo | None:
        """The latest published release, or ``None`` on any failure."""
        request = urllib.request.Request(
            RELEASES_LATEST_URL, headers={"Accept": ACCEPT_HEADER}
        )
        try:
            with self._opener(request, REQUEST_TIMEOUT_SECONDS) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, ValueError):
            return None
        if not isinstance(payload, dict):
            return None
        tag = payload.get("tag_name")
        page_url = payload.get("html_url")
        if not isinstance(tag, str) or not tag:
            return None
        if not isinstance(page_url, str) or not page_url:
            return None
        version = tag[1:] if tag[:1] in ("v", "V") else tag
        return ReleaseInfo(
            version=version,
            page_url=page_url,
            assets=_parse_assets(payload.get("assets")),
        )
