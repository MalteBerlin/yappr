from __future__ import annotations

from yappr.checks.base import CheckResult
from yappr.peec.models import PeecData


def run(data: PeecData) -> CheckResult:
    return CheckResult(
        id="diversity",
        name="Source Diversity",
        score=0,
        weight=0.20,
        summary="Not implemented yet.",
        raw={"project_id": data.project_id},
    )
