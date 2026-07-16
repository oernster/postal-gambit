"""Invariant 2: the domain is pure. No I/O, no clocks, no randomness."""

from __future__ import annotations

import ast

from tests.structural.scan import imports_of, iter_modules, parse, relative_name

FORBIDDEN_DOMAIN_IMPORTS = {
    "os",
    "pathlib",
    "io",
    "logging",
    "time",
    "random",
    "secrets",
    "uuid",
    "threading",
    "multiprocessing",
    "asyncio",
    "socket",
    "subprocess",
    "sqlite3",
    "json",
}

FORBIDDEN_CALLS = {
    ("datetime", "now"),
    ("datetime", "utcnow"),
    ("date", "today"),
    ("uuid", "uuid4"),
}


class TestDomainPurity:
    def test_no_impure_imports(self) -> None:
        problems = []
        for path in iter_modules("domain"):
            for module in sorted(imports_of(path)):
                if module.split(".")[0] in FORBIDDEN_DOMAIN_IMPORTS:
                    problems.append(f"{relative_name(path)} imports {module}")
        assert problems == []

    def test_no_wall_clock_or_randomness_calls(self) -> None:
        problems = []
        for path in iter_modules("domain"):
            for node in ast.walk(parse(path)):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                if not isinstance(func, ast.Attribute):
                    continue
                owner = func.value
                if (
                    isinstance(owner, ast.Name)
                    and (owner.id, func.attr) in FORBIDDEN_CALLS
                ):
                    problems.append(
                        f"{relative_name(path)}:{node.lineno} calls "
                        f"{owner.id}.{func.attr}()"
                    )
        assert problems == []
