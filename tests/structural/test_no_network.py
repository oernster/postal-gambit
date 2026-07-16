"""Invariant 4: no network code anywhere. The mail client is the transport."""

from __future__ import annotations

from tests.structural.scan import imports_of, iter_modules, relative_name

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
    def test_no_module_imports_networking(self) -> None:
        problems = []
        for path in iter_modules():
            for module in sorted(imports_of(path)):
                root = module.split(".")[0]
                if root in FORBIDDEN_NETWORK_ROOTS or any(
                    module == m or module.startswith(m + ".")
                    for m in FORBIDDEN_NETWORK_MODULES
                ):
                    problems.append(f"{relative_name(path)} imports {module}")
        assert problems == []
