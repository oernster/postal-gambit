"""The user's own identity, stamped into PGN tags of games they create."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Identity:
    name: str = ""
    email: str = ""

    @property
    def is_configured(self) -> bool:
        return bool(self.name.strip())
