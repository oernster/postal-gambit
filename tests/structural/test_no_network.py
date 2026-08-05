"""Invariant 4: no network code anywhere. The mail client is the transport.

The scope is everything a user installs, not just the package. The claim on
the site and in the README is about the product, so a "check for updates"
button in the setup program or an analytics call in the composition root has
to fail this suite the same way one in the package would.
"""

from __future__ import annotations

from tests.structural.scan import (
    DELIVERY_SCRIPTS,
    imports_of,
    iter_shipped_modules,
    relative_name,
)

FORBIDDEN_NETWORK_ROOTS = {
    "socket",
    "ssl",
    "http",
    "smtplib",
    "imaplib",
    "poplib",
    "ftplib",
    "telnetlib",
    "xmlrpc",
    "requests",
    "httpx",
    "aiohttp",
    "urllib3",
}
FORBIDDEN_NETWORK_MODULES = {"urllib.request", "urllib.error"}


class TestNoNetwork:
    def test_no_shipped_module_imports_networking(self) -> None:
        problems = []
        for path in iter_shipped_modules():
            for module in sorted(imports_of(path)):
                root = module.split(".")[0]
                if root in FORBIDDEN_NETWORK_ROOTS or any(
                    module == m or module.startswith(m + ".")
                    for m in FORBIDDEN_NETWORK_MODULES
                ):
                    problems.append(f"{relative_name(path)} imports {module}")
        assert problems == []


class TestScopeOfTheClaim:
    """The invariant is only as good as the surface it is proven over, so the
    surface is asserted rather than assumed. Narrowing the scan back to the
    package has to fail here rather than pass quietly."""

    def test_the_scan_reaches_beyond_the_package(self) -> None:
        scanned = {relative_name(path) for path in iter_shipped_modules()}
        assert "main.py" in scanned
        assert "installer_main.py" in scanned
        assert any(name.startswith("postalgambit/") for name in scanned)
        assert any(name.startswith("installer/") for name in scanned)

    def test_the_delivery_scripts_are_the_only_exemption(self) -> None:
        scanned = {relative_name(path) for path in iter_shipped_modules()}
        assert scanned.isdisjoint(DELIVERY_SCRIPTS)

    def test_build_output_is_not_mistaken_for_source(self) -> None:
        scanned = {relative_name(path) for path in iter_shipped_modules()}
        assert not any("payload" in name.split("/") for name in scanned)
