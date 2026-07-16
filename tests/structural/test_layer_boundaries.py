"""Invariant 1 and 3: layering direction and third-party quarantine."""

from __future__ import annotations

from pathlib import Path

from tests.structural.scan import imports_of, is_stdlib, iter_modules, relative_name

RULES_ADAPTER = "postalgambit/infrastructure/rules_pychess.py"


def _violations(
    subpackage: str,
    allowed_internal_prefixes: tuple[str, ...],
    allowed_third_party_roots: tuple[str, ...] = (),
) -> list[str]:
    problems = []
    for path in iter_modules(subpackage):
        for module in sorted(imports_of(path)):
            if is_stdlib(module):
                continue
            if module.split(".")[0] in allowed_third_party_roots:
                continue
            if module == "postalgambit" or any(
                module == p or module.startswith(p + ".")
                for p in allowed_internal_prefixes
            ):
                continue
            problems.append(f"{relative_name(path)} imports {module}")
    return problems


class TestLayering:
    def test_domain_imports_stdlib_and_domain_only(self) -> None:
        assert _violations("domain", ("postalgambit.domain",)) == []

    def test_application_never_imports_infrastructure_or_ui(self) -> None:
        allowed = ("postalgambit.domain", "postalgambit.application")
        assert _violations("application", allowed) == []

    def test_infrastructure_never_imports_ui(self) -> None:
        allowed = (
            "postalgambit.domain",
            "postalgambit.application",
            "postalgambit.infrastructure",
        )
        assert _violations("infrastructure", allowed, ("chess",)) == []

    def test_ui_is_a_client_of_application_only(self) -> None:
        # postalgambit.version is app identity, not a layer; any layer that
        # shows the name or version to the user may read it.
        allowed = (
            "postalgambit.domain",
            "postalgambit.application",
            "postalgambit.ui",
            "postalgambit.version",
        )
        assert _violations("ui", allowed, ("PySide6",)) == []

    def test_package_root_modules_are_stdlib_only(self) -> None:
        problems = []
        for path in iter_modules():
            if path.parent.name != "postalgambit":
                continue
            for module in sorted(imports_of(path)):
                if not is_stdlib(module):
                    problems.append(f"{relative_name(path)} imports {module}")
        assert problems == []


class TestQuarantine:
    def test_python_chess_lives_in_one_adapter_only(self) -> None:
        offenders = [
            relative_name(path)
            for path in iter_modules()
            if any(m.split(".")[0] == "chess" for m in imports_of(path))
            and relative_name(path) != RULES_ADAPTER
        ]
        assert offenders == []

    def test_pyside6_lives_in_the_ui_layer_only(self) -> None:
        offenders = [
            relative_name(path)
            for path in iter_modules()
            if any(m.split(".")[0] == "PySide6" for m in imports_of(path))
            and not relative_name(path).startswith("postalgambit/ui/")
        ]
        assert offenders == []

    def test_main_is_the_only_composition_root(self) -> None:
        offenders = [
            relative_name(path)
            for path in iter_modules()
            if any(
                m.startswith("postalgambit.infrastructure") for m in imports_of(path)
            )
            and not relative_name(path).startswith("postalgambit/infrastructure/")
        ]
        assert offenders == []

    def test_main_py_exists_at_the_repo_root(self) -> None:
        from tests.structural.scan import REPO_ROOT

        assert (REPO_ROOT / "main.py").is_file()
        assert not (Path(REPO_ROOT) / "postalgambit" / "main.py").exists()
