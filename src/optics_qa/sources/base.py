from __future__ import annotations

from typing import Protocol

from ..models import RawPost


class PostSource(Protocol):
    def fetch(self, limit: int = 100) -> list[RawPost]: ...
