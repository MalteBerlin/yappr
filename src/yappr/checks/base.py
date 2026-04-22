from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from yappr.peec.models import PeecData


class CheckResult(BaseModel):
    id: str
    name: str
    score: int
    weight: float
    summary: str
    details: list[str] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)


class Check(Protocol):
    def run(self, data: PeecData) -> CheckResult: ...
