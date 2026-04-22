from __future__ import annotations

from yappr.checks.base import CheckResult
from yappr.peec.models import PeecData


def run(data: PeecData) -> CheckResult:
    total_sources = len(data.all_domain_sources)
    if total_sources == 0:
        return CheckResult(
            id="gap",
            name="Competitive Gap",
            score=0,
            weight=0.15,
            summary="No source data yet for gap analysis.",
            raw={},
        )

    gap_sources_count = len(data.gap_sources)
    gap_ratio = gap_sources_count / total_sources
    score = round((1 - gap_ratio) * 100)
    summary = f"{gap_sources_count} competitor-cited sources where you're absent."
    return CheckResult(
        id="gap",
        name="Competitive Gap",
        score=score,
        weight=0.15,
        summary=summary,
        raw={
            "gap_sources_count": gap_sources_count,
            "total_sources_count": total_sources,
            "gap_ratio": gap_ratio,
        },
    )
