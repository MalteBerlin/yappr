from __future__ import annotations

from yappr.checks.base import CheckResult
from yappr.peec.models import PeecData


def run(data: PeecData) -> CheckResult:
    return CheckResult(
        id="sentiment",
        name="Sentiment",
        score=0,
        weight=0.15,
        summary="Not implemented yet.",
        raw={"project_id": data.project_id},
    )
