"""Tests for the wall-clock and id-generation adapters."""

from __future__ import annotations

from datetime import datetime, timezone

from postalgambit.domain.game import GameId
from postalgambit.infrastructure.clock import SystemClock
from postalgambit.infrastructure.ids import Uuid4Generator


class TestSystemClock:
    def test_now_is_aware_utc(self) -> None:
        now = SystemClock().now()
        assert now.tzinfo == timezone.utc
        assert abs((now - datetime.now(timezone.utc)).total_seconds()) < 5


class TestUuid4Generator:
    def test_ids_are_canonical_and_unique(self) -> None:
        generator = Uuid4Generator()
        first, second = generator.new_id(), generator.new_id()
        GameId(first)
        GameId(second)
        assert first != second
