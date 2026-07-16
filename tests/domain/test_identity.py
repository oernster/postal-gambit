"""Unit tests for the user identity value object."""

from __future__ import annotations

from postalgambit.domain.identity import Identity


class TestIdentity:
    def test_defaults_are_unconfigured(self) -> None:
        assert Identity().is_configured is False

    def test_whitespace_name_is_unconfigured(self) -> None:
        assert Identity(name="   ").is_configured is False

    def test_named_identity_is_configured(self) -> None:
        assert Identity(name="Oliver", email="o@example.org").is_configured is True
