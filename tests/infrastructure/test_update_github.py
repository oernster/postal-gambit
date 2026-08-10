"""Tests for the GitHub releases adapter, with the opener faked.

The adapter is the one module exempt from the no-network invariant, so its
tests never touch the network either: the opener is injected.
"""

from __future__ import annotations

import json
import urllib.request
from typing import Any, Self

from postalgambit.infrastructure.update_github import (
    ACCEPT_HEADER,
    RELEASES_LATEST_URL,
    REQUEST_TIMEOUT_SECONDS,
    GitHubReleaseSource,
)


class FakeResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None


class FakeOpener:
    def __init__(self, body: bytes | None = None, error: Exception | None = None):
        self._body = body
        self._error = error
        self.request: urllib.request.Request | None = None
        self.timeout: float | None = None

    def __call__(self, request: urllib.request.Request, timeout: float) -> Any:
        self.request = request
        self.timeout = timeout
        if self._error is not None:
            raise self._error
        return FakeResponse(self._body or b"")


def payload(**overrides: Any) -> bytes:
    data: dict[str, Any] = {
        "tag_name": "v1.1.0",
        "html_url": "https://example.test/rel",
        "assets": [
            {
                "name": "PostalGambitSetup.exe",
                "browser_download_url": "https://example.test/win",
            }
        ],
    }
    data.update(overrides)
    return json.dumps(data).encode("utf-8")


def test_happy_path_parses_release_and_strips_v() -> None:
    source = GitHubReleaseSource(opener=FakeOpener(payload()))
    release = source.latest_release()
    assert release is not None
    assert release.version == "1.1.0"
    assert release.page_url == "https://example.test/rel"
    assert release.assets[0].name == "PostalGambitSetup.exe"
    assert release.assets[0].download_url == "https://example.test/win"


def test_a_bare_tag_is_kept_as_written() -> None:
    source = GitHubReleaseSource(opener=FakeOpener(payload(tag_name="1.1.0")))
    release = source.latest_release()
    assert release is not None
    assert release.version == "1.1.0"


def test_request_targets_the_endpoint_with_header_and_timeout() -> None:
    opener = FakeOpener(payload())
    GitHubReleaseSource(opener=opener).latest_release()
    assert opener.request is not None
    assert opener.request.full_url == RELEASES_LATEST_URL
    assert opener.request.get_header("Accept") == ACCEPT_HEADER
    assert opener.timeout == REQUEST_TIMEOUT_SECONDS


def test_failures_read_as_no_release() -> None:
    assert GitHubReleaseSource(FakeOpener(error=OSError())).latest_release() is None
    assert GitHubReleaseSource(FakeOpener(b"not json")).latest_release() is None
    assert GitHubReleaseSource(FakeOpener(b"[1]")).latest_release() is None


def test_missing_or_wrongly_typed_fields_read_as_no_release() -> None:
    for override in (
        {"tag_name": None},
        {"tag_name": ""},
        {"tag_name": 7},
        {"html_url": None},
        {"html_url": ""},
        {"html_url": 7},
    ):
        source = GitHubReleaseSource(FakeOpener(payload(**override)))
        assert source.latest_release() is None, override


def test_malformed_assets_are_filtered_not_fatal() -> None:
    body = payload(
        assets=[
            "not a dict",
            {"name": "", "browser_download_url": "https://example.test/x"},
            {"name": "no-url.exe"},
            {"name": 7, "browser_download_url": "https://example.test/y"},
            {"name": "bad-url.exe", "browser_download_url": 7},
            {"name": "empty-url.exe", "browser_download_url": ""},
            {"name": "good.exe", "browser_download_url": "https://example.test/g"},
        ]
    )
    release = GitHubReleaseSource(FakeOpener(body)).latest_release()
    assert release is not None
    assert [asset.name for asset in release.assets] == ["good.exe"]


def test_assets_absent_or_non_list_read_as_empty() -> None:
    for override in ({"assets": None}, {"assets": "nope"}):
        release = GitHubReleaseSource(FakeOpener(payload(**override))).latest_release()
        assert release is not None
        assert release.assets == ()


def test_default_opener_is_urlopen(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_urlopen(request: urllib.request.Request, timeout: float) -> Any:
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        return FakeResponse(payload())

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    release = GitHubReleaseSource().latest_release()
    assert release is not None
    assert captured["url"] == RELEASES_LATEST_URL
    assert captured["timeout"] == REQUEST_TIMEOUT_SECONDS
