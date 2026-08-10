"""Invariant 4: no network code anywhere. The mail client is the transport.

The scope is everything a user installs, not just the package. The claim on
the site and in the README is about the product, so an analytics call in the
setup program or the composition root has to fail this suite the same way
one in the package would.

The single disclosed exception is the update check's GitHub adapter, named
in UPDATE_CHECK_EXEMPT_MODULE below. The exemption is itself asserted: the
module must exist, must be the reason for the exemption (it imports
urllib.request) and must import nothing forbidden beyond what the exemption
grants, so the hole can neither widen nor outlive its purpose. This is a
deliberate product decision, disclosed in the README, ARCHITECTURE.md and
on the site: the transport claim is about your games and moves, which
still travel only by mail.
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

# The one module allowed to touch the network, and the only imports the
# exemption grants it.
UPDATE_CHECK_EXEMPT_MODULE = "postalgambit/infrastructure/update_github.py"
UPDATE_CHECK_ALLOWED_IMPORTS = {"urllib.request"}


def _forbidden_imports_of(path) -> list[str]:
    found = []
    for module in sorted(imports_of(path)):
        root = module.split(".")[0]
        if root in FORBIDDEN_NETWORK_ROOTS or any(
            module == m or module.startswith(m + ".") for m in FORBIDDEN_NETWORK_MODULES
        ):
            found.append(module)
    return found


class TestNoNetwork:
    def test_no_shipped_module_imports_networking(self) -> None:
        problems = []
        for path in iter_shipped_modules():
            if relative_name(path) == UPDATE_CHECK_EXEMPT_MODULE:
                continue
            for module in _forbidden_imports_of(path):
                problems.append(f"{relative_name(path)} imports {module}")
        assert problems == []


class TestUpdateCheckExemption:
    """The exemption is a claim about one module, so it is asserted whole."""

    def test_the_exempt_module_ships(self) -> None:
        scanned = {relative_name(path) for path in iter_shipped_modules()}
        assert UPDATE_CHECK_EXEMPT_MODULE in scanned

    def test_the_exemption_has_not_outlived_its_reason(self) -> None:
        for path in iter_shipped_modules():
            if relative_name(path) == UPDATE_CHECK_EXEMPT_MODULE:
                assert "urllib.request" in imports_of(path)
                return
        raise AssertionError("exempt module not found in the scan")

    def test_the_exemption_grants_nothing_beyond_its_purpose(self) -> None:
        for path in iter_shipped_modules():
            if relative_name(path) == UPDATE_CHECK_EXEMPT_MODULE:
                extras = [
                    module
                    for module in _forbidden_imports_of(path)
                    if module not in UPDATE_CHECK_ALLOWED_IMPORTS
                ]
                assert extras == []
                return
        raise AssertionError("exempt module not found in the scan")


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
