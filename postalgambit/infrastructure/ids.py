"""Id generation adapter: the only place randomness is drawn."""

from __future__ import annotations

import uuid


class Uuid4Generator:
    def new_id(self) -> str:
        return str(uuid.uuid4())
