"""Unit tests for the subject-line builder."""

from __future__ import annotations

import pytest

from postalgambit.domain.errors import DomainError
from postalgambit.domain.subject import build_subject
from postalgambit.domain.wire import WireAction

SHORT_ID = "5f3a9c2e"


class TestBuildSubject:
    def test_move_subject(self) -> None:
        subject = build_subject(SHORT_ID, WireAction.MOVE, move_number=14, san="Nxe5")
        assert subject == "[Postal Gambit 5f3a9c2e] move 14: Nxe5"

    @pytest.mark.parametrize(
        "action, phrase",
        [
            (WireAction.INVITE, "invitation"),
            (WireAction.DRAW_ACCEPT, "draw accepted"),
            (WireAction.RESIGN, "resignation"),
        ],
    )
    def test_non_move_subjects(self, action: WireAction, phrase: str) -> None:
        assert build_subject(SHORT_ID, action) == f"[Postal Gambit 5f3a9c2e] {phrase}"

    def test_move_subject_requires_number_and_san(self) -> None:
        with pytest.raises(DomainError):
            build_subject(SHORT_ID, WireAction.MOVE)
