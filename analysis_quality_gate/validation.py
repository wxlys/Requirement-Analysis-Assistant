from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    path: str = ""
    level: str = "error"
    test_point_id: str | None = None
    gap_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {key: value for key, value in asdict(self).items() if value is not None}
