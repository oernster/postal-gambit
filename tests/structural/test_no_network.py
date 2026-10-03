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

import ast

import pytest

from tests.structural.scan import (
    DELIVERY_SCRIPTS,
    imports_of,
    iter_shipped_modules,
    parse,
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

# Routes round a plain import denylist that round 3 measured passing: an
# event loop that opens sockets, a way to import a module by a computed name,
# a way to run another program and a way to make the browser fetch.
FORBIDDEN_INDIRECT_ROOTS = {
    "asyncio",
    "importlib",
    "multiprocessing",
    "socketserver",
    "subprocess",
    "webbrowser",
    "wsgiref",
}
DYNAMIC_IMPORT_CALL = "__import__"

# Qt's own networking. The single-instance channel uses the local-socket
# classes, which never leave the machine, so those two names are granted and
# nothing else from the module is.
QT_NETWORK_MODULE = "PySide6.QtNetwork"
QT_LOCAL_SOCKET_NAMES = {"QLocalServer", "QLocalSocket"}
QT_NETWORK_PREFIXES = (
    QT_NETWORK_MODULE,
    "PySide6.QtWeb",
    "PySide6.QtHttpServer",
    "PySide6.QtNetworkAuth",
    "PySide6.QtRemoteObjects",
)

# Modules that run another program, each for one named reason. Asserted
# below: each must still need it, so the grant cannot outlive its reason.
PROCESS_LAUNCH_GRANTS = {
    "postalgambit/ui/dialogs/export_dialog.py": "mailto hand-off to xdg-open",
    "installer/ops/commands.py": "the setup program's CommandRunner seam",
}
PROCESS_LAUNCH_MODULE = "subprocess"

# The one module allowed to touch the network, with the only imports the
# exemption grants it.
UPDATE_CHECK_EXEMPT_MODULE = "postalgambit/infrastructure/update_github.py"
UPDATE_CHECK_ALLOWED_IMPORTS = {"urllib.request"}


def _is_qt_network(module: str) -> bool:
    return any(
        module == prefix or module.startswith(prefix) for prefix in QT_NETWORK_PREFIXES
    )


def _qt_and_dynamic_routes(path) -> list[str]:
    """Qt networking by any spelling, plus `__import__` calls."""
    found = []
    for node in ast.walk(parse(path)):
        if isinstance(node, ast.Import):
            found += [a.name for a in node.names if _is_qt_network(a.name)]
        elif isinstance(node, ast.ImportFrom) and node.module == "PySide6":
            named = (f"PySide6.{a.name}" for a in node.names)
            found += [module for module in named if _is_qt_network(module)]
        elif isinstance(node, ast.ImportFrom) and node.module == QT_NETWORK_MODULE:
            found += [
                f"{QT_NETWORK_MODULE}.{a.name}"
                for a in node.names
                if a.name not in QT_LOCAL_SOCKET_NAMES
            ]
        elif isinstance(node, ast.ImportFrom) and _is_qt_network(node.module or ""):
            found.append(node.module)
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == DYNAMIC_IMPORT_CALL
        ):
            found.append(f"{DYNAMIC_IMPORT_CALL}()")
    return found


def _forbidden_imports_of(path) -> list[str]:
    found = []
    for module in sorted(imports_of(path)):
        root = module.split(".")[0]
        if (
            root in FORBIDDEN_NETWORK_ROOTS
            or root in FORBIDDEN_INDIRECT_ROOTS
            or any(
                module == m or module.startswith(m + ".")
                for m in FORBIDDEN_NETWORK_MODULES
            )
        ):
            found.append(module)
    return found + _qt_and_dynamic_routes(path)


class TestNoNetwork:
    def test_no_shipped_module_imports_networking(self) -> None:
        problems = []
        for path in iter_shipped_modules():
            name = relative_name(path)
            if name == UPDATE_CHECK_EXEMPT_MODULE:
                continue
            for module in _forbidden_imports_of(path):
                if module == PROCESS_LAUNCH_MODULE and name in PROCESS_LAUNCH_GRANTS:
                    continue
                problems.append(f"{name} imports {module}")
        assert problems == []

    def test_each_process_launch_grant_is_still_needed(self) -> None:
        shipped = {relative_name(path): path for path in iter_shipped_modules()}
        for name in PROCESS_LAUNCH_GRANTS:
            assert name in shipped, f"{name} is granted but no longer ships"
            assert PROCESS_LAUNCH_MODULE in imports_of(shipped[name])


_PLANTS = {
    "qt_network_client": "from PySide6.QtNetwork import QNetworkAccessManager\n",
    "qt_network_module": "import PySide6.QtNetwork\n",
    "qt_network_from_package": "from PySide6 import QtNetwork\n",
    "asyncio": "import asyncio\n",
    "importlib": "import importlib\nimportlib.import_module('soc' + 'ket')\n",
    "dunder_import": "__import__('soc' + 'ket')\n",
    "subprocess": "import subprocess\n",
    "webbrowser": "import webbrowser\n",
}


class TestTheScannerBites:
    """Positive controls: each route round an import denylist that round 3
    measured passing is planted in a scratch module and must be flagged."""

    @pytest.mark.parametrize("source", _PLANTS.values(), ids=_PLANTS.keys())
    def test_planted_route_is_flagged(self, tmp_path, source: str) -> None:
        plant = tmp_path / "plant.py"
        plant.write_text(source, encoding="utf-8")
        assert _forbidden_imports_of(plant) != []

    def test_the_local_socket_is_not_networking(self, tmp_path) -> None:
        plant = tmp_path / "plant.py"
        plant.write_text(
            "from PySide6.QtNetwork import QLocalServer, QLocalSocket\n",
            encoding="utf-8",
        )
        assert _forbidden_imports_of(plant) == []


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
